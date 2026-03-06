def get_next_step(proc, step_index):
    """Return the step at step_index, or None if out of range."""
    steps = proc.get("steps") or []
    if step_index < len(steps):
        return steps[step_index]
    return None


def get_step_context(proc, step_index):
    """Return dict with current step, total steps, and step_index for templates."""
    steps = proc.get("steps") or []
    current = get_next_step(proc, step_index)
    return {
        "current_step": current,
        "step_index": step_index,
        "total_steps": len(steps),
        "has_next": step_index + 1 < len(steps),
    }
