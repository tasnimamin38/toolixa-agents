"""Deterministic validation of bounded task dependency graphs."""
from __future__ import annotations
from collections import deque
from typing import Any
from toolixa_core.tools.base import ToolCallContext,ToolSpec

def order_task_graph(tasks:list[dict[str,Any]],*,max_tasks:int=100)->list[str]:
 if not isinstance(tasks,list) or len(tasks)>max_tasks: raise ValueError(f"tasks must be a list with at most {max_tasks} entries")
 identifiers=[]; dependencies={}
 for item in tasks:
  if not isinstance(item,dict): raise ValueError("each task must be an object")
  task_id,required=item.get("id"),item.get("depends_on",[])
  if not isinstance(task_id,str) or not task_id.strip(): raise ValueError("every task requires a non-empty id")
  if task_id in dependencies: raise ValueError(f"duplicate task id: {task_id}")
  if not isinstance(required,list) or not all(isinstance(value,str) for value in required): raise ValueError(f"depends_on for {task_id} must be a list of strings")
  if task_id in required: raise ValueError(f"task cannot depend on itself: {task_id}")
  identifiers.append(task_id); dependencies[task_id]=required
 known=set(identifiers)
 for task_id,required in dependencies.items():
  missing=sorted(set(required)-known)
  if missing: raise ValueError(f"task {task_id} has missing dependencies: {', '.join(missing)}")
 dependents={task_id:[] for task_id in identifiers}; indegree={task_id:len(set(required)) for task_id,required in dependencies.items()}
 for task_id,required in dependencies.items():
  for dependency in required: dependents[dependency].append(task_id)
 ready=deque(task_id for task_id in identifiers if indegree[task_id]==0); ordered=[]
 while ready:
  current=ready.popleft(); ordered.append(current)
  for dependent in dependents[current]:
   indegree[dependent]-=1
   if indegree[dependent]==0: ready.append(dependent)
 if len(ordered)!=len(identifiers):
  cyclic=sorted(task_id for task_id,degree in indegree.items() if degree>0)
  raise ValueError(f"dependency cycle detected: {', '.join(cyclic)}")
 return ordered

class ValidateTaskGraphTool:
 spec=ToolSpec("orchestration.validate_task_graph","Validate identifiers, dependencies, missing edges and cycles; return deterministic execution order without executing tasks or spawning agents.",(),{"type":"object","properties":{"tasks":{"type":"array","minItems":1,"maxItems":100,"items":{"type":"object","properties":{"id":{"type":"string","minLength":1,"maxLength":120},"depends_on":{"type":"array","maxItems":100,"items":{"type":"string","minLength":1,"maxLength":120}}},"required":["id"],"additionalProperties":False}}},"required":["tasks"],"additionalProperties":False})
 def invoke(self,arguments:dict[str,Any],context:ToolCallContext)->dict[str,Any]:
  del context
  tasks=arguments["tasks"]
  return {"task_count":len(tasks),"execution_order":order_task_graph(tasks),"validated":True,"tasks_executed":False,"agents_spawned":0}
