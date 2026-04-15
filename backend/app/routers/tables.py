from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.table import Table
from app.models.user import UserRole
from app.schemas.table import TableCreate, TableUpdate, TableResponse

router = APIRouter(prefix="/tables", tags=["tables"])

MANAGER_ONLY = [Depends(require_role(UserRole.MANAGER))]
STAFF_ONLY = [Depends(require_role(UserRole.WAITER, UserRole.MANAGER))]


@router.post("/", response_model=TableResponse, status_code=201, dependencies=MANAGER_ONLY)
async def create_table(data: TableCreate, db: AsyncSession = Depends(get_db)):
    table = Table(**data.model_dump())
    db.add(table)
    await db.commit()
    await db.refresh(table)
    return table


@router.get("/", response_model=list[TableResponse])
async def list_tables(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table))
    return result.scalars().all()


@router.get("/{table_id}", response_model=TableResponse)
async def get_table(table_id: int, db: AsyncSession = Depends(get_db)):
    table = await db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    return table


@router.patch("/{table_id}", response_model=TableResponse, dependencies=STAFF_ONLY)
async def update_table(table_id: int, data: TableUpdate, db: AsyncSession = Depends(get_db)):
    table = await db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(table, key, value)
    await db.commit()
    await db.refresh(table)
    return table
