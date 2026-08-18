from typing import Dict, Any, List, Optional

class XlsBlock:
    def __init__(self, page: str, x: int, y: int, value: Any):
        self.page = page
        self.top = y
        self.bottom = y
        self.left = x
        self.right = x
        self.style_refer_block: Optional['XlsBlock'] = None
        self.value = value
        self.properties: Dict[str, Any] = {}

    @classmethod
    def from_context(cls, context: 'XlsBlockBuildContext', value: Any) -> 'XlsBlock':
        return cls(context.page, context.x, context.y, value)

    def region(self, left: int, top: int, right: int, bottom: int) -> 'XlsBlock':
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        return self

    def span(self, width: int, height: int) -> 'XlsBlock':
        self.right = self.left + max(0, width - 1)
        self.bottom = self.top + max(0, height - 1)
        return self

    def value(self, value: Any) -> 'XlsBlock':
        self.value = value
        return self

    def add_property(self, name: str, value: Any) -> 'XlsBlock':
        self.properties[name] = value
        return self

    def set_property(self, name: str, value: Any) -> None:
        self.properties[name] = value

    def style(self, style: 'XlsBlock') -> 'XlsBlock':
        self.style_refer_block = style
        return self

    def width(self) -> int:
        return self.right - self.left + 1

    def height(self) -> int:
        return self.bottom - self.top + 1

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def to_json_value(self) -> Dict[str, Any]:
        d = {
            "page": self.page,
            "top": self.top,
            "bottom": self.bottom,
            "left": self.left,
            "right": self.right,
            "value": self.value,
        }
        if self.style_refer_block:
            d["styleReferBlock"] = self.style_refer_block.to_json_value()
        if self.properties:
            d["properties"] = self.properties
        return d

class XlsBlockBuildContext:
    def __init__(self, page: str, x: int, y: int):
        self.start_x = max(0, x)
        self.x = self.start_x
        self.y = max(0, y)
        self.page = page

    @classmethod
    def from_page(cls, page: str) -> 'XlsBlockBuildContext':
        return cls(page, 0, 0)

    def next(self) -> 'XlsBlockBuildContext':
        context = XlsBlockBuildContext(self.page, self.start_x, self.y)
        context.x = self.x + 1
        return context

    def new_line(self) -> 'XlsBlockBuildContext':
        context = XlsBlockBuildContext(self.page, self.start_x, self.y + 1)
        context.x = 0
        return context

    def next_line(self) -> 'XlsBlockBuildContext':
        context = XlsBlockBuildContext(self.page, self.start_x, self.y + 1)
        context.x = self.start_x
        return context

    def to_block(self, value: Any) -> XlsBlock:
        return XlsBlock.from_context(self, value)

class XlsPage:
    def __init__(self, name: str):
        self.name = name
        self.blocks: List[XlsBlock] = []

    def add_block(self, block: XlsBlock) -> 'XlsPage':
        self.blocks.append(block)
        return self

    def push_block(self, block: XlsBlock) -> None:
        self.blocks.append(block)

    def block_at(self, x: int, y: int) -> Optional[XlsBlock]:
        for block in self.blocks:
            if block.contains(x, y):
                return block
        return None
        
    def to_json_value(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "blocks": [b.to_json_value() for b in self.blocks]
        }

class XlsWorkbook:
    def __init__(self):
        self.pages: List[XlsPage] = []

    def add_page(self, page: XlsPage) -> 'XlsWorkbook':
        self.pages.append(page)
        return self

    def push_page(self, page: XlsPage) -> None:
        self.pages.append(page)

    def page(self, name: str) -> Optional[XlsPage]:
        for p in self.pages:
            if p.name == name:
                return p
        return None

    def to_json_value(self) -> Dict[str, Any]:
        return {
            "pages": [p.to_json_value() for p in self.pages]
        }
