import pytest
from teaql.core.xls import XlsWorkbook, XlsPage, XlsBlock, XlsBlockBuildContext

def test_xls_block_creation():
    block = XlsBlock.from_context(XlsBlockBuildContext.from_page("Sheet1"), "Hello")
    assert block.page == "Sheet1"
    assert block.value == "Hello"
    assert block.left == 0
    assert block.top == 0
    
    block.region(1, 1, 3, 3)
    assert block.width() == 3
    assert block.height() == 3
    assert block.contains(2, 2) is True
    assert block.contains(0, 0) is False

def test_xls_context_navigation():
    context = XlsBlockBuildContext.from_page("Sheet1")
    assert context.x == 0 and context.y == 0
    
    context = context.next()
    assert context.x == 1 and context.y == 0
    
    context = context.new_line()
    assert context.x == 0 and context.y == 1
    
    # Start offset testing
    context = XlsBlockBuildContext("Sheet2", 2, 2)
    assert context.x == 2 and context.y == 2
    context = context.next_line()
    assert context.x == 2 and context.y == 3

def test_xls_workbook_structure():
    wb = XlsWorkbook()
    page = XlsPage("MyPage")
    block = XlsBlock("MyPage", 0, 0, "Data")
    page.add_block(block)
    wb.add_page(page)
    
    assert wb.page("MyPage") is not None
    assert wb.page("MyPage").block_at(0, 0) is not None
    assert wb.page("MyPage").block_at(1, 1) is None
    
    json_val = wb.to_json_value()
    assert len(json_val["pages"]) == 1
    assert json_val["pages"][0]["name"] == "MyPage"
    assert len(json_val["pages"][0]["blocks"]) == 1
