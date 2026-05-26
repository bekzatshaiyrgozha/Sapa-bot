from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

from bot.db import models


def test_models_create_tables_and_insert():
    engine = create_engine("sqlite:///:memory:")

    # Replace any JSONB column types with generic JSON so SQLite can compile DDL
    for table in models.Base.metadata.tables.values():
        for col in table.columns:
            tname = getattr(col.type, "__visit_name__", None) or col.type.__class__.__name__
            if tname.upper() == "JSONB":
                col.type = sa.JSON()

    models.Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    u = models.User(id=12345, full_name="Test User", role="teacher")
    session.add(u)
    session.commit()

    got = session.query(models.User).filter_by(id=12345).one()
    assert got.full_name == "Test User"

    s = models.Subject(name="Math", bm_id=12345)
    session.add(s)
    session.commit()

    assert session.query(models.Subject).count() == 1
