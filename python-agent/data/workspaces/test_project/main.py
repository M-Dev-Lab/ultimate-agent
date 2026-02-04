from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="test_project", version="1.0.0")

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

items: List[Item] = []

@app.get("/")
async def root():
    return {"message": "Welcome to test_project", "version": "1.0.0"}

@app.get("/items")
async def get_items():
    return items

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items")
async def create_item(item: Item):
    items.append(item)
    return item

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items):
        if item.id == item_id:
            deleted = items.pop(i)
            return {"deleted": deleted}
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
