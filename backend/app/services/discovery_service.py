from typing import List, Dict, Any
import numpy as np
import pandas as pd
from app.services.llm_service import narrate_dataset_facts_with_gemini

def discover_dataset_facts(df: pd.DataFrame, dataset_name: str) -> List[Dict[str, Any]]:
    """
    Discovery Engine for Requirement 2:
    - Finds most related variables (Pearson & Spearman correlations)
    - Detects unique data facts (Pareto 80/20 concentration, categorical dominance, high volatility)
    - Synthesizes findings and enriches them via Gemini into plain-English takeaways
    """
    facts: List[Dict[str, Any]] = []

    if df.empty or len(df) < 3:
        return facts

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c])]

    # 1. Correlation Discovery (Related Variables)
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr(method='pearson')
        pairs = []
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                c1, c2 = numeric_cols[i], numeric_cols[j]
                val = corr_matrix.loc[c1, c2]
                if not np.isnan(val):
                    pairs.append((c1, c2, float(val), abs(float(val))))

        # Sort by absolute correlation strength
        pairs.sort(key=lambda x: x[3], reverse=True)

        # Highlight top relationships
        for c1, c2, r, abs_r in pairs[:3]:
            if abs_r >= 0.20:
                if r >= 0.70:
                    title = f"Strong Direct Relationship: {c1.replace('_', ' ').title()} & {c2.replace('_', ' ').title()}"
                    desc = f"'{c1}' and '{c2}' move strongly together with a correlation of {r:.2f}. When one increases, the other shows a reliable rise."
                elif r >= 0.40:
                    title = f"Moderate Positive Link: {c1.replace('_', ' ').title()} & {c2.replace('_', ' ').title()}"
                    desc = f"'{c1}' exhibits a positive co-movement with '{c2}' (correlation: {r:.2f})."
                elif r <= -0.70:
                    title = f"Strong Inverse Trade-Off: {c1.replace('_', ' ').title()} vs {c2.replace('_', ' ').title()}"
                    desc = f"'{c1}' and '{c2}' exhibit a significant opposing relationship ({r:.2f}). As one increases, the other drops sharply."
                else:
                    title = f"Inverse Trend: {c1.replace('_', ' ').title()} vs {c2.replace('_', ' ').title()}"
                    desc = f"An inverse relationship ({r:.2f}) was detected between '{c1}' and '{c2}'."

                facts.append({
                    "fact_type": "CORRELATION",
                    "title": title,
                    "description": desc,
                    "metric_value": f"r = {r:+.2f}"
                })

    # 2. Pareto 80/20 & Concentration Discovery
    if categorical_cols and numeric_cols:
        for cat in categorical_cols[:3]:
            for num in numeric_cols[:3]:
                grouped = df.groupby(cat)[num].sum().sort_values(ascending=False)
                total_sum = grouped.sum()
                if total_sum > 0 and len(grouped) >= 2:
                    cum_sum = grouped.cumsum()
                    threshold = total_sum * 0.75
                    categories_for_75 = int((cum_sum <= threshold).sum()) + 1
                    pct_categories = (categories_for_75 / len(grouped)) * 100
                    
                    if pct_categories <= 50.0:
                        facts.append({
                            "fact_type": "PARETO_80_20",
                            "title": f"Concentration in {cat.replace('_', ' ').title()}",
                            "description": f"The top {categories_for_75} {cat.replace('_', ' ')} groups ({pct_categories:.0f}% of categories) account for {threshold / total_sum * 100:.0f}% of total {num.replace('_', ' ')}.",
                            "metric_value": f"Top {pct_categories:.0f}% drives major share"
                        })
                        break

    # 3. Categorical Distribution / Dominance
    for cat in categorical_cols:
        counts = df[cat].value_counts(normalize=True)
        if not counts.empty:
            top_val = counts.index[0]
            top_pct = counts.iloc[0] * 100
            if top_pct >= 40.0:
                facts.append({
                    "fact_type": "DOMINANCE",
                    "title": f"Leading Segment: {str(top_val)[:20]} in {cat.replace('_', ' ').title()}",
                    "description": f"'{top_val}' constitutes {top_pct:.1f}% of all records in '{cat}', establishing it as the primary operational group.",
                    "metric_value": f"{top_pct:.0f}% share"
                })
                break

    # 4. Distribution Quirk & Volatility
    if numeric_cols:
        cv_scores = []
        for num in numeric_cols:
            mean_val = float(df[num].mean())
            std_val = float(df[num].std())
            if mean_val != 0:
                cv = abs(std_val / mean_val)
                cv_scores.append((num, cv, mean_val, std_val))
        
        cv_scores.sort(key=lambda x: x[1], reverse=True)
        if cv_scores:
            num, cv, mean_val, std_val = cv_scores[0]
            facts.append({
                "fact_type": "QUIRK",
                "title": f"Distribution Profile: {num.replace('_', ' ').title()}",
                "description": f"'{num}' averages {mean_val:.1f} with standard deviation {std_val:.1f} (dispersion index {cv:.2f}x).",
                "metric_value": f"Avg: {mean_val:.1f}"
            })

    # 5. Enrich with Gemini plain-English narrator
    polished_facts = narrate_dataset_facts_with_gemini(facts, dataset_name)
    return polished_facts
