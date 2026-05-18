import asyncio
import sys
import argparse
import os

from executor.engine import WorkflowEngine

async def main():
    parser = argparse.ArgumentParser(description="Agentic Workflow Engine")
    parser.add_argument("command", choices=["run", "benchmark", "serve"], help="Command to execute")
    parser.add_argument("goal", nargs="?", help="The goal to execute (for run command)")
    parser.add_argument("--budget", type=float, default=None, help="Budget for the workflow")
    parser.add_argument("--no-approval", action="store_true", help="Skip human approval gates")
    
    args = parser.parse_args()
    
    if args.command == "run":
        if not args.goal:
            print("Error: 'run' requires a goal.")
            sys.exit(1)
        
        engine = WorkflowEngine()
        print(f"Goal: {args.goal}")
        
        result = await engine.run(
            goal=args.goal,
            budget=args.budget,
            require_approval=not args.no-approval
        )
        
        print("\n" + "="*50)
        if result.success:
            print("✅ Workflow Complete!")
        else:
            print(f"❌ Workflow Failed: {result.reason}")
            
        print(f"Total Cost: ${result.total_cost:.4f}")
        print(f"Total Tokens: {result.total_tokens}")
        print(f"Duration: {result.total_duration:.1f}s")
        print(f"Tasks: {result.completed_count}/{result.subtask_count} completed")
        print("="*50)
        
        if result.output:
            print("\nResult:")
            print("-" * 50)
            print(result.output)
            print("-" * 50)
            
            # Save output to file
            os.makedirs("output/results", exist_ok=True)
            output_file = f"output/results/workflow_{int(result.total_duration)}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.output)
            print(f"\nSaved to: {output_file}")

    elif args.command == "benchmark":
        print("Benchmark not fully implemented in CLI yet.")
        
    elif args.command == "serve":
        print("Server mode not implemented yet.")

if __name__ == "__main__":
    asyncio.run(main())
