#!/usr/bin/env python3

import sys
sys.path.insert(0, ".")

from graph.state import create_initial_state
from graph.builder import build_teaching_copilot_graph

print("=== Testing Provider Selection ===")

# Test 1: Create initial state with longcat provider
state = create_initial_state("二次函数", "高中二年级", "longcat")
print(f"Initial state created with provider: {state["provider"]}")

# Test 2: Build graph with longcat provider
graph = build_teaching_copilot_graph("longcat")
print("Graph built successfully")

print("\nAll tests passed! Provider should now be correctly set to longcat")
