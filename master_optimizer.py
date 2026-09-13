from master_engine import run


def optimize(input_path=None, output_dir="optimizer_output", base_plan=None):
    """Backward-compatible entry point for Master Engine 3.0."""
    return run(input_path, output_dir=output_dir)


if __name__ == "__main__":
    print("MASTER OPTIMIZER 3.0 -> Master Engine 3.0")
