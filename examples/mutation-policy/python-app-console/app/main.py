"""Approve a customer and its contact preference in the same transaction."""
import asyncio
from datetime import datetime, timezone
import json
import os

from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import (
    DelegatingMutationPolicyApprovalProvider,
    DelegatingMutationPolicyRegistry,
    MutationDecision,
    MutationPolicyApproval,
    MutationPolicyApprovalStatus,
    MutationPolicyError,
    MutationPolicyIdentity,
    UserContext,
)

BLOCKED_EMAIL = "blocked@example.com"
POLICY_KEY = "Customer.saveGraph"
DENIAL = "CUSTOMER_EMAIL_BLOCKED"


class CustomerApproval:
    identity = MutationPolicyIdentity("example.customer-onboarding", "1", "sha256:customer-onboarding-v1")

    def __init__(self):
        self.reviewed = []

    def review(self, context, plan):
        self.reviewed.append(len(plan.operations))
        if (
            plan.request_key != POLICY_KEY
            or plan.root_entity_type != "Customer"
            or sorted(operation.entity for operation in plan.operations) != ["Customer", "CustomerContact"]
            or any(operation.kind.value != "create" for operation in plan.operations)
        ):
            return MutationDecision.denied("CUSTOMER_GRAPH_INCOMPLETE", "profile and contact are both required")
        profile = next(operation for operation in plan.operations if operation.entity == "Customer")
        email = profile.changed_values["email"].try_text()
        if email == BLOCKED_EMAIL:
            return MutationDecision.denied(DENIAL, "reserved customer email", "Customer.email")
        return MutationDecision.allowed()


class ApprovalAudit:
    def __init__(self):
        self.events = []

    async def on_safe_event(self, context, event):
        self.events.append(event)


async def prepare_customer(context, email, channel):
    customer = await (
        Q.customers().comment("Initialize the customer profile")
        .purpose("Prepare one governed customer onboarding submission").new_entity(context)
    )
    customer.update_platform(1).update_email(email)
    contact = await (
        Q.customer_contacts().comment("Initialize the contact preference")
        .purpose("Include the consent data in the same customer submission").new_entity(context)
    )
    contact.update_customer(customer.id).update_channel(channel)
    customer.customer_contact_list().append(contact)
    return customer


async def profile_by_email(context, email):
    return await (
        Q.customers().with_email_is(email).limit(2).comment("Read a customer profile by email")
        .purpose("Check what was persisted after business approval").execute_for_one(context)
    )


async def main():
    service = create_sqlite_service(os.environ["TEAQL_DATABASE_CONNECTION_STRING"])
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", service)
    await context.ensure_schema()

    policy, audit = CustomerApproval(), ApprovalAudit()
    context.with_mutation_policy_registry(
        DelegatingMutationPolicyRegistry(lambda key: policy if key == POLICY_KEY else None)
    ).with_mutation_policy_approval_provider(
        DelegatingMutationPolicyApprovalProvider(
            lambda identity: MutationPolicyApproval(
                identity, "customer-review-owner", datetime(2026, 10, 1, tzinfo=timezone.utc)
            ) if identity == policy.identity else None
        )
    ).with_app_audit_event_sink(audit)

    label = os.environ["TEAQL_SHOWCASE_ROUND"]
    email, channel = f"approved-{label}@example.com", f"Email-{label}"
    approved = await prepare_customer(context, email, channel)
    await approved.audit_as("Approve customer onboarding and its contact preference").save(context)

    blocked = await prepare_customer(context, BLOCKED_EMAIL, f"Rejected-{label}")
    try:
        await blocked.audit_as("Review the blocked customer onboarding submission").save(context)
    except MutationPolicyError as error:
        assert DENIAL in str(error)
    else:
        raise AssertionError("The blocked customer graph was accepted")

    assert policy.reviewed == [2, 2]
    assert len(audit.events) == 2
    for event in audit.events:
        snapshot = event.mutation_governance
        assert snapshot.policy == policy.identity and len(snapshot.operations) == 2
        assert snapshot.approval_status == MutationPolicyApprovalStatus.APPROVED

    found = await profile_by_email(context, email)
    assert found is not None and found.id == approved.id and found.email == email
    contact = await (
        Q.customer_contacts().filter_by_customer(found.id).with_channel_is(channel).limit(2)
        .comment("Read the approved contact preference")
        .purpose("Confirm it was saved with its customer").execute_for_one(context)
    )
    assert contact is not None and contact.channel == channel

    assert await profile_by_email(context, BLOCKED_EMAIL) is None
    rejected_contact = await (
        Q.customer_contacts().with_channel_is(f"Rejected-{label}").limit(2)
        .comment("Look for a contact belonging to the denied submission")
        .purpose("Verify policy rejection left both business tables unchanged").execute_for_one(context)
    )
    assert rejected_contact is None
    print("CUSTOMER_APPROVAL=" + json.dumps(dict(
        round=label, customerId=found.id, email=email, contactId=contact.id, channel=channel,
        reviewedOperations=policy.reviewed, approvedAudits=len(audit.events), denial=DENIAL,
    )))


if __name__ == "__main__":
    asyncio.run(main())
