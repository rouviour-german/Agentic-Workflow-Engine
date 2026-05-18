from planner.dag import SubtaskNode, WorkflowDAG, SubtaskStatus

class DependencyNotReadyError(Exception): pass
class InvalidMappingError(Exception): pass
class MissingInputError(Exception): pass

class DependencyResolver:
    def resolve_inputs(self, node: SubtaskNode, dag: WorkflowDAG) -> dict[str, str]:
        resolved = {}
        for input_name, source_ref in node.input_mapping.items():
            source_node_id, field = source_ref.rsplit(".", 1)
            source_node = dag.get_node(source_node_id)
            
            if source_node.status != SubtaskStatus.COMPLETED:
                raise DependencyNotReadyError(f"Input '{input_name}' depends on '{source_node_id}' which is {source_node.status}")
                
            if field == "output":
                resolved[input_name] = source_node.output or ""
            else:
                raise InvalidMappingError(f"Unknown field: {field}")
                
        return resolved

    def render_prompt(self, node: SubtaskNode, resolved_inputs: dict[str, str]) -> str:
        try:
            return node.prompt_template.format(**resolved_inputs)
        except KeyError as e:
            # We must leave the prompt as is if not full mappings
            import string
            formatter = string.Formatter()
            keys = [i[1] for i in formatter.parse(node.prompt_template) if i[1] is not None]
            safe_inputs = {k: resolved_inputs.get(k, f"{{{k}}}") for k in keys}
            return node.prompt_template.format(**safe_inputs)
