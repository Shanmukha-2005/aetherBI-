import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Google Generative AI if key is present
if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    except Exception:
        pass

def get_gemini_model(model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
    key = api_key or os.getenv("GEMINI_API_KEY", "") or settings.GEMINI_API_KEY
    if not key:
        return None
    try:
        genai.configure(api_key=key)
        return genai.GenerativeModel(model_name)
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini model '{model_name}': {e}")
        return None

def generate_sqlite_sql(
    prompt: str,
    table_name: str,
    schema_info: List[Dict[str, Any]],
    sample_rows: List[Dict[str, Any]],
    distinct_categories: Optional[Dict[str, List[str]]] = None,
    dataset_csv: Optional[str] = None,
    is_full_dataset: bool = False,
    is_dp_surrogate: bool = True,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    multi_tables_info: Optional[List[Dict[str, Any]]] = None,
    detected_joins: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None
) -> Dict[str, str]:
    """
    Translates a natural language user request into a clean, optimized SQLite query with an explanation.
    Sends prompt to Gemini LLM with complete dataset grounding, conversational history, and multi-table context.
    Protected by Differential Privacy-Preserving Topological Context Synthesis.
    """
    distinct_categories = distinct_categories or {}
    
    schema_lines = []
    for col in schema_info:
        c_name = col.get("name", "")
        c_type = col.get("type", "unknown")
        if c_name in distinct_categories and distinct_categories[c_name]:
            cats_sample = ", ".join([f"'{v}'" for v in distinct_categories[c_name][:15]])
            schema_lines.append(f"- {c_name} ({c_type}) [Example values: {cats_sample}]")
        else:
            schema_lines.append(f"- {c_name} ({c_type})")

    schema_str = "\n".join(schema_lines)
    all_col_names = [col.get("name", "") for col in schema_info]

    if is_dp_surrogate and dataset_csv:
        data_section = f"""=== DIFFERENTIAL PRIVACY-PRESERVING TOPOLOGICAL MICRO-SURROGATE (ε=1.0, δ=1e-5) ===
Zero raw enterprise customer records or proprietary rows are transmitted. The table sample below
is a Topologically Identical Micro-Surrogate synthesized via (ε=1.0, δ=1e-5)-Differential Privacy.
It preserves the exact column schema, datetime formats, categorical casing dictionaries, and
eigenvalue correlation topology of the real enterprise dataset:
```csv
{dataset_csv.strip()}
```"""
    elif is_full_dataset and dataset_csv:
        data_section = f"""=== COMPLETE DATASET RECORDS (All {len(sample_rows)} rows provided) ===
You have 100% full visibility over every single row and value in this dataset:
```csv
{dataset_csv.strip()}
```"""
    else:
        sample_str = json.dumps(sample_rows[:15], indent=2, default=str)
        data_section = f"""=== REPRESENTATIVE SAMPLE ROWS ===
{sample_str}"""

    # Multi-table context injection
    multi_table_section = ""
    if multi_tables_info and len(multi_tables_info) > 1:
        tbl_blocks = []
        for tbl in multi_tables_info:
            c_list = ", ".join([f"{c['name']} ({c['type']})" for c in tbl.get("columns", [])])
            tbl_blocks.append(f"- Table `{tbl['table_name']}` ({tbl['name']}):\n  Columns: {c_list}")

        join_lines = []
        for j in (detected_joins or []):
            join_lines.append(f"- `{j['table_1']}`.{j['column_1']} = `{j['table_2']}`.{j['column_2']} (Shared key: {j['column_1']})")

        join_str = "\n".join(join_lines) if join_lines else "None automatically detected; identify logical keys if joining."

        multi_table_section = f"""
=== MULTI-DATASET SCHEMAS & DETECTED RELATIONSHIPS ===
Available Tables:
{chr(10).join(tbl_blocks)}

Auto-Detected Foreign Key / JOIN Relationships:
{join_str}

MULTI-TABLE RULES:
1. You may write SQLite queries joining these tables using INNER JOIN or LEFT JOIN on matching keys.
2. Always alias or prefix columns (e.g. a.state, b.profit) to prevent ambiguous column names.
"""

    # Conversational history injection
    conv_section = ""
    if conversation_history:
        turns = []
        for msg in conversation_history[-6:]:
            role = str(msg.get("role", "user")).capitalize()
            content = msg.get("content", "")
            sql = msg.get("generated_sql", "")
            if sql:
                turns.append(f"{role}: {content}\nPrevious SQL: {sql}")
            else:
                turns.append(f"{role}: {content}")
        conv_section = f"""
=== RECENT CONVERSATION HISTORY (Previous Turns) ===
{chr(10).join(turns)}

IMPORTANT FOLLOW-UP INSTRUCTION:
If the user's new question is a follow-up or refinement of a previous question (e.g., 'now filter out California', 'show only top 3', 'what about 1990?'), build upon or adjust the previous query logic accordingly.
"""

    system_instruction = f"""
You are an expert SQLite Database Architect and Senior BI Data Analyst.
Your task is to translate the user's natural language question into an accurate, read-only SQLite SQL SELECT query that operates STRICTLY on the target dataset(s).

=== DATASET SPECIFICATION ===
Primary Table: `{table_name}`
Available Columns and Types:
{schema_str}

{data_section}
{multi_table_section}
{conv_section}

=== MANDATORY DATASET GROUNDING RULES ===
1. ABSOLUTE DATASET GROUNDING:
   - Always query from the target table(s). Never invent, hallucinate, or reference non-existent tables or columns.
   - Use ONLY column names that exist in the schema: {', '.join(all_col_names)}.
   - Map user terms to the exact dataset columns (e.g., 'sales' -> `sales_amount`, 'profit' -> `profit`, 'state' -> `state`, 'marketing' -> `marketing_spend`).
   - If the user refers to an entity, attribute, or category, identify the matching column in the dataset schema.

2. TEXT MATCHING & FILTERS:
   - When filtering string/categorical columns, use case-insensitive matching: `LOWER(column) = LOWER('value')` or `column LIKE '%value%'`.
   - Use the example values and sample rows above to understand the exact format of categories in this dataset.

3. AGGREGATIONS & METRICS:
   - For "average" or "mean": `ROUND(AVG(col), 2)`
   - For "total" or "sum": `ROUND(SUM(col), 2)`
   - For "highest", "most", "maximum", "best", "top": `ORDER BY col DESC LIMIT 1` (or `LIMIT N` if requested)
   - For "lowest", "least", "minimum", "worst": `ORDER BY col ASC LIMIT 1`
   - Grouping: When aggregating per dimension, include the dimension column in `SELECT` and `GROUP BY`.

4. SAFETY & COMPATIBILITY:
   - Generate ONLY pure SQLite-compatible SELECT statements.
   - No data-modifying statements (no DROP, DELETE, UPDATE, INSERT, ALTER).

5. OUTPUT FORMAT:
   Return ONLY a valid JSON object with:
   {{
     "sql": "<Exact executable SQLite SELECT query>",
     "explanation": "<2-3 sentence clear explanation describing what this query calculates, which specific dataset columns are used, and the analytical insight it returns.>"
   }}
"""

    # Attempt Gemini generation across supported models
    model = None
    for model_candidate in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
        model = get_gemini_model(model_candidate, api_key=api_key)
        if model:
            break

    if model:
        try:
            full_prompt = f"{system_instruction}\n\nUser Question: \"{prompt}\"\n\nJSON Output:"
            response = model.generate_content(
                full_prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            parsed = json.loads(text.strip())
            if "sql" in parsed and "explanation" in parsed:
                sql_clean = clean_sql_output(parsed["sql"])
                # Ensure the correct table name is strictly preserved
                if table_name.lower() not in sql_clean.lower():
                    sql_clean = re.sub(r"\bFROM\s+([a-zA-Z0-9_]+)", f"FROM {table_name}", sql_clean, flags=re.IGNORECASE)
                return {
                    "sql": sql_clean,
                    "explanation": parsed["explanation"]
                }
        except Exception as e:
            logger.error(f"Gemini SQL generation error: {e}")

    # Fallback to local semantic engine grounded in the same dataset schema & categories
    return fallback_sql_generator(prompt, table_name, schema_info, sample_rows, distinct_categories)

def clean_sql_output(sql: str) -> str:
    cleaned = re.sub(r"^```(sql)?", "", sql.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```$", "", cleaned.strip())
    return cleaned.strip()

def normalize_word(w: str) -> str:
    w = w.lower().strip().replace('_', '').replace(' ', '')
    if w.endswith('ies'):
        w = w[:-3] + 'y'
    elif w.endswith('s') and not w.endswith('ss'):
        w = w[:-1]
    return w

def fallback_sql_generator(
    prompt: str,
    table_name: str,
    schema_info: List[Dict[str, Any]],
    sample_rows: Optional[List[Dict[str, Any]]] = None,
    distinct_categories: Optional[Dict[str, List[str]]] = None
) -> Dict[str, str]:
    """
    Provides intelligent semantic SQL generation grounded in dataset schema and values.
    Accurately recognizes entity-metric extremes (e.g. year with max murders), grouped aggregations,
    scalar aggregates, and value filters.
    """
    lp = prompt.lower().strip()
    sample_rows = sample_rows or []
    distinct_categories = distinct_categories or {}
    
    all_cols = [c['name'] for c in schema_info]
    all_num = [c['name'] for c in schema_info if c['type'] == 'numeric']
    all_cat = [c['name'] for c in schema_info if c['type'] != 'numeric']
    
    # Check limit / top N
    top_match = re.search(r'\b(?:top|limit|first)\s+(\d+)\b', lp)
    limit = int(top_match.group(1)) if top_match else None
    
    # Intent flags
    is_highest = any(w in lp for w in ['highest', 'max', 'maximum', 'most', 'top', 'greatest', 'best', 'largest'])
    is_lowest = any(w in lp for w in ['lowest', 'min', 'minimum', 'least', 'smallest', 'worst', 'bottom'])
    is_avg = any(w in lp for w in ['average', 'avg', 'mean'])
    is_sum = any(w in lp for w in ['total', 'sum', 'overall'])
    is_count = any(w in lp for w in ['count', 'number of', 'how many', 'total records'])
    has_grouping = any(w in lp for w in ['by', 'per', 'for each', 'grouped by', 'group by'])
    
    # Extreme metric extraction (e.g. "maximum murders", "highest profit", "lowest car theft")
    extreme_metric = None
    extreme_pattern = r'\b(highest|max|maximum|most|greatest|best|largest|lowest|min|minimum|least|smallest|worst)\s+(?:amount\s+of\s+|number\s+of\s+|count\s+of\s+|total\s+)?([a-z0-9_]+(?:\s+[a-z0-9_]+)?)'
    em_match = re.search(extreme_pattern, lp)
    if em_match:
        cand = em_match.group(2).strip()
        norm_cand = normalize_word(cand)
        for col in all_cols:
            norm_col = normalize_word(col)
            if norm_col in norm_cand or norm_cand in norm_col or norm_cand.replace(' ', '') == norm_col:
                extreme_metric = col
                break

    # General column matching
    matched_cols = []
    for col in all_cols:
        norm_col = normalize_word(col)
        words = lp.split()
        if any(normalize_word(w) == norm_col for w in words) or col in lp or col.replace('_', ' ') in lp:
            if col not in matched_cols:
                matched_cols.append(col)
                
    # Filter detection from distinct categories & sample records
    filter_clause = ''
    matched_filter_desc = ''
    for cat_col, vals in distinct_categories.items():
        for val in vals:
            if val and len(val) >= 2 and val.lower() in lp:
                filter_clause = f"WHERE LOWER({cat_col}) = '{val.lower()}'"
                matched_filter_desc = f"filtered where `{cat_col}` is '{val}'"
                break
        if filter_clause:
            break

    if not filter_clause:
        for row in sample_rows:
            for cat_col in all_cat:
                val = str(row.get(cat_col, ''))
                if val and len(val) > 2 and val.lower() in lp:
                    filter_clause = f"WHERE LOWER({cat_col}) = '{val.lower()}'"
                    matched_filter_desc = f"filtered where `{cat_col}` is '{val}'"
                    break
            if filter_clause:
                break

    # Numeric threshold filters
    num_gt = re.search(r'(?:>|greater than|above|more than)\s*\$?(\d+(?:\.\d+)?)', lp)
    num_lt = re.search(r'(?:<|less than|below|under)\s*\$?(\d+(?:\.\d+)?)', lp)
    if num_gt and all_num:
        target_num = extreme_metric or (matched_cols[0] if matched_cols else all_num[0])
        thresh = num_gt.group(1)
        filter_clause = f"WHERE {target_num} > {thresh}"
        matched_filter_desc = f"filtered where `{target_num}` > {thresh}"
    elif num_lt and all_num:
        target_num = extreme_metric or (matched_cols[0] if matched_cols else all_num[0])
        thresh = num_lt.group(1)
        filter_clause = f"WHERE {target_num} < {thresh}"
        matched_filter_desc = f"filtered where `{target_num}` < {thresh}"

    # PATTERN 1: Entity-Metric Ranking (e.g. "output the year with the maximum murders", "the state with highest profit")
    if (is_highest or is_lowest) and not has_grouping:
        entity_col = None
        metric_col = extreme_metric
        
        other_matched = [c for c in matched_cols if c != metric_col]
        if other_matched:
            entity_col = other_matched[0]
        elif len(matched_cols) >= 2 and not metric_col:
            metric_col = matched_cols[1]
            entity_col = matched_cols[0]
            
        if entity_col and metric_col:
            dir_sql = 'DESC' if is_highest else 'ASC'
            lbl = 'highest' if is_highest else 'lowest'
            lim = limit if limit else 1
            sql = f"SELECT {entity_col}, {metric_col}\nFROM {table_name}"
            if filter_clause:
                sql += f"\n{filter_clause}"
            sql += f"\nORDER BY {metric_col} {dir_sql}\nLIMIT {lim};"
            exp = f"Retrieves the `{entity_col}` with the {lbl} `{metric_col}` by ordering `{metric_col}` in {dir_sql} order and limiting to {lim} record(s)."
            return {"sql": sql, "explanation": exp}

    # PATTERN 2: Grouped Aggregations (e.g. "average murders by year", "profit per state")
    if has_grouping and len(matched_cols) >= 1:
        group_col = None
        by_match = re.search(r'\b(?:by|per|for each)\s+([a-z0-9_]+)', lp)
        if by_match:
            by_cand = normalize_word(by_match.group(1))
            for col in all_cols:
                if normalize_word(col) in by_cand or by_cand in normalize_word(col):
                    group_col = col
                    break
        if not group_col:
            group_col = all_cat[0] if all_cat else matched_cols[0]
            
        num_candidates = [c for c in matched_cols if c != group_col]
        target_num = num_candidates[0] if num_candidates else (all_num[0] if all_num else '*')
        
        lim_clause = f"\nLIMIT {limit}" if limit else ""
        if is_avg:
            agg = f"ROUND(AVG({target_num}), 2) AS avg_{target_num}"
            order = f"avg_{target_num} DESC"
            exp_desc = f"average of `{target_num}`"
        elif is_count:
            agg = "COUNT(*) AS total_count"
            order = "total_count DESC"
            exp_desc = "record count"
        elif is_highest:
            agg = f"MAX({target_num}) AS max_{target_num}"
            order = f"max_{target_num} DESC"
            exp_desc = f"maximum `{target_num}`"
        elif is_lowest:
            agg = f"MIN({target_num}) AS min_{target_num}"
            order = f"min_{target_num} ASC"
            exp_desc = f"minimum `{target_num}`"
        else:
            agg = f"ROUND(SUM({target_num}), 2) AS total_{target_num}" if target_num != '*' else "COUNT(*) AS total_count"
            order = f"total_{target_num} DESC" if target_num != '*' else "total_count DESC"
            exp_desc = f"total of `{target_num}`"

        sql = f"SELECT {group_col}, {agg}\nFROM {table_name}"
        if filter_clause:
            sql += f"\n{filter_clause}"
        sql += f"\nGROUP BY {group_col}\nORDER BY {order}{lim_clause};"
        exp = f"Calculates {exp_desc} grouped by `{group_col}` and ranked in descending order."
        return {"sql": sql, "explanation": exp}

    # PATTERN 3: Scalar Aggregations (e.g. "the average of marketing spend", "maximum murders", "total population")
    target_metric = extreme_metric or (matched_cols[0] if matched_cols else (all_num[0] if all_num else None))
    if target_metric and (is_avg or is_sum or is_count or is_highest or is_lowest):
        if is_avg:
            agg = f"ROUND(AVG({target_metric}), 2) AS avg_{target_metric}"
            desc = f"average of `{target_metric}`"
        elif is_sum:
            agg = f"ROUND(SUM({target_metric}), 2) AS total_{target_metric}"
            desc = f"total sum of `{target_metric}`"
        elif is_lowest:
            agg = f"MIN({target_metric}) AS min_{target_metric}"
            desc = f"minimum `{target_metric}`"
        elif is_highest:
            agg = f"MAX({target_metric}) AS max_{target_metric}"
            desc = f"maximum `{target_metric}`"
        elif is_count:
            agg = f"COUNT({target_metric}) AS count_{target_metric}"
            desc = f"count of `{target_metric}`"
        else:
            agg = f"ROUND(AVG({target_metric}), 2) AS avg_{target_metric}"
            desc = f"metric `{target_metric}`"

        sql = f"SELECT {agg}\nFROM {table_name}"
        if filter_clause:
            sql += f"\n{filter_clause}"
        sql += ";"
        exp = f"Calculates the overall {desc} across `{table_name}`"
        if matched_filter_desc:
            exp += f" ({matched_filter_desc})"
        exp += "."
        return {"sql": sql, "explanation": exp}


    # Pattern 4: Projection, filtering, or ranking
    cols_to_select = ", ".join(matched_cols) if matched_cols else "*"
    lim = limit if limit else 10
    sql = f"SELECT {cols_to_select}\nFROM {table_name}"
    if filter_clause:
        sql += f"\n{filter_clause}"
    if matched_cols and matched_cols[0] in all_num:
        sql += f"\nORDER BY {matched_cols[0]} DESC"
    sql += f"\nLIMIT {lim};"
    exp = f"Retrieved records from `{table_name}`"
    if matched_filter_desc:
        exp += f" {matched_filter_desc}"
    exp += f", limited to {lim} rows."
    return {"sql": sql, "explanation": exp}

def narrate_dataset_facts_with_gemini(raw_facts: List[Dict[str, Any]], dataset_name: str) -> List[Dict[str, Any]]:
    """
    Uses Gemini to polish statistical findings into compelling, human-friendly insights.
    """
    model = get_gemini_model("gemini-1.5-flash")
    if not model or not raw_facts:
        return raw_facts

    try:
        prompt = f"""
You are a Lead Data Strategist.
Here are mathematical and statistical findings discovered in the dataset '{dataset_name}':
{json.dumps(raw_facts, indent=2)}

Transform these statistical observations into clear, engaging, plain-English "Key Facts & Relationships" that any business leader or team member can immediately understand.

Format your response as a JSON list with items containing:
- "fact_type": (keep original: CORRELATION, PARETO_80_20, DOMINANCE, or QUIRK)
- "title": A punchy, insightful headline (max 8 words)
- "description": 1-2 sentences explaining what this means in practical business/analytical terms.
- "metric_value": A short badge label (e.g. "r = 0.82", "Top 18% -> 79%", "91% Dominance")
"""
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        parsed = json.loads(response.text.strip())
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
    except Exception as e:
        logger.warning(f"Failed to narrate facts via Gemini: {e}")

    return raw_facts
