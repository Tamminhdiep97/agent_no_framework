def render_mermaid_trace(trace):
    lines = ["```mermaid", "flowchart TD"]
    lines.append(f'    A["User: {trace["user_input"]}"]')
    lines.append('    A --> B["PlannerAgent"]')

    agent_logs = trace.get("agent_logs", [])
    plan = trace.get("plan", [])

    # Map step index to its log (assume order matches)
    for i, step in enumerate(plan):
        agent = step["agent"]
        lines.append(f'    B --> C{i}["{agent}"]')

        # Find the i-th log entry (since agent_logs is in execution order)
        if i < len(agent_logs):
            log_entry = agent_logs[i]
            tool_calls = log_entry.get("tool_calls", [])
            if tool_calls:
                for j, call in enumerate(tool_calls):
                    tool_name = call["tool_call"]["name"]
                    result_preview = call["result"].replace('"', "'")
                    lines.append(f'    C{i} --> D{i}_{j}["CallCheck: {tool_name}"]')
                    lines.append(f'    D{i}_{j} --> E{i}_{j}["Result: {result_preview}..."]')
                    lines.append(f'    E{i}_{j} --> F{i}["{agent} Output"]')
            else:
                lines.append(f'    C{i} --> F{i}["{agent} Output"]')
        else:
            lines.append(f'    C{i} --> F{i}["{agent} Output"]')

    # Synthesizer
    if plan:
        lines.append('    F0 --> G["SynthesizerAgent"]')
        for i in range(1, len(plan)):
            lines.append(f'    F{i} --> G')
        final_preview = trace["final_answer"].replace("\n", " ")
        lines.append(f'    G --> H["Final Answer: {final_preview}..."]')

    lines.append("```")
    return "\n".join(lines)


def save_mermaid_to_md(mermaid_code: str, output_path: str = "trace.md"):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("```mermaid\n")
        f.write(mermaid_code.strip())
        f.write("\n```\n")
    print(f"✅ Mermaid diagram saved to {output_path}")
