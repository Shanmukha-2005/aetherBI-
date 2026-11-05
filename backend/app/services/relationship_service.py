import json
import logging
from typing import List, Dict, Any
import pandas as pd
from sqlalchemy.orm import Session
from app.db.session import engine
from app.models.dataset import Dataset

logger = logging.getLogger(__name__)

def discover_dataset_relationships(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Scans all datasets belonging to the user and identifies potential JOIN keys
    based on column name similarity, type compatibility, and distinct value overlaps.
    """
    datasets = db.query(Dataset).filter(Dataset.user_id == user_id).all()
    if len(datasets) < 2:
        return []

    relationships = []

    for i in range(len(datasets)):
        for j in range(i + 1, len(datasets)):
            d1 = datasets[i]
            d2 = datasets[j]

            meta1 = json.loads(d1.columns_meta or "[]")
            meta2 = json.loads(d2.columns_meta or "[]")

            for c1 in meta1:
                name1 = c1.get("name", "").lower().strip()
                type1 = c1.get("type", "")

                for c2 in meta2:
                    name2 = c2.get("name", "").lower().strip()
                    type2 = c2.get("type", "")

                    # Check type compatibility
                    if type1 != type2 and not (type1 in ["numeric", "integer"] and type2 in ["numeric", "integer"]):
                        continue

                    # Check name match or common key patterns
                    is_name_match = (
                        name1 == name2 or
                        name1.replace("_", "") == name2.replace("_", "") or
                        (name1.endswith("_id") and name2.endswith("_id") and name1 == name2) or
                        (name1 == "id" and name2 == f"{d1.name.lower().replace(' ', '_')}_id") or
                        (name2 == "id" and name1 == f"{d2.name.lower().replace(' ', '_')}_id")
                    )

                    if not is_name_match:
                        continue

                    # Verify actual distinct value overlap in SQLite
                    try:
                        sql = f"""
                        SELECT COUNT(DISTINCT a."{c1['name']}") AS overlap
                        FROM "{d1.physical_table_name}" a
                        INNER JOIN "{d2.physical_table_name}" b ON a."{c1['name']}" = b."{c2['name']}"
                        WHERE a."{c1['name']}" IS NOT NULL AND b."{c2['name']}" IS NOT NULL
                        """
                        overlap_df = pd.read_sql_query(sql, con=engine)
                        overlap_count = int(overlap_df.iloc[0]["overlap"])

                        if overlap_count > 0:
                            relationships.append({
                                "dataset_1_id": d1.id,
                                "dataset_1_name": d1.name,
                                "table_1": d1.physical_table_name,
                                "column_1": c1["name"],
                                "dataset_2_id": d2.id,
                                "dataset_2_name": d2.name,
                                "table_2": d2.physical_table_name,
                                "column_2": c2["name"],
                                "overlap_count": overlap_count,
                                "relationship_type": "SHARED_KEY",
                                "description": f"Shared key '{c1['name']}' with {overlap_count} overlapping distinct values"
                            })
                    except Exception as err:
                        logger.debug(f"Error checking overlap between {d1.id}:{c1['name']} and {d2.id}:{c2['name']}: {err}")

    return relationships
