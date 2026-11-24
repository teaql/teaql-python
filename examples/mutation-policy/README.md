# Approve a customer profile and contact preference

Install the customer approval policy and its exact approval in the trusted
Context. The generated Q APIs prepare a customer and contact preference, then
save them together with a business audit reason. The approved pair is read
back by email and customer ID. The blocked email is denied with
`CUSTOMER_EMAIL_BLOCKED` and neither record is saved. The application observes
the two operations at policy review and checks the successful audit snapshot.

- `model.xml` owns the domain model.
- `python-lib-core/` holds the generated domain library.
- `python-app-console/app/main.py` runs the business scenario.
- `python-app-console/calibration/` retains the original runtime probe.

The SDK inventory runs both entry points. The focused Conformance gate runs
the console twice against one fresh SQLite database and independently checks
the persisted records.
