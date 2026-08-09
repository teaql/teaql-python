import pytest
from teaql.core.graph import GraphNode, EntityGraphOperation

def test_graph_node_operations():
    node = GraphNode("User")
    
    # Test set and value
    node.set("id", 123)
    node.set("name", "Alice")
    assert node.value("id") == 123
    assert node.id() == 123
    
    # Test children and relations
    child1 = node.child("posts")
    child1.set("id", 1)
    
    child2 = node.reference("comments", 456)
    assert child2.id() == 456
    
    assert "posts" in node.relations()
    assert "comments" in node.relations()
    
    # Test remove
    node.remove("comments")
    assert "comments" not in node.relations()
    
    # Test operation and delete
    assert node.operation() == EntityGraphOperation.SAVE
    node.delete()
    assert node.operation() == EntityGraphOperation.DELETE
    
    # Test comments
    node.comment("this is a test")
    assert node.comment_text == "this is a test"
    node.set_comment("updated test")
    assert node.comment_text == "updated test"
