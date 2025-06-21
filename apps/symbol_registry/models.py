from datetime import datetime, timedelta
from sqlmodel import Field, SQLModel

class Symbol(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    repo: str
    branch: str
    fq_name: str
    kind: str
    file_path: str
    status: str = "reserved"   # reserved | active | deprecated
    plan_id: str | None = None
    reserved_until: datetime | None = None
    commit_sha: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)