def build_prompt(cr, snippets):
    ctx = "\n\n".join(snippets)
    return f"""# CHANGE REQUEST
{cr.description}

# CONTEXT
{ctx}

Return plan JSON."""