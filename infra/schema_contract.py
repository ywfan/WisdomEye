import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

class SchemaContract:
    """Loads a JSON schema and provides validate/conform helpers."""
    def __init__(self, schema_path: str = "modules/resume_json/schema.json"):
        self.schema_path = schema_path
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Read schema JSON from disk; return empty on failure."""
        p = Path(self.schema_path)
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _is_string_annot(self, v: Any) -> bool:
        return isinstance(v, str)

    def _template_for(self, node: Any) -> Any:
        if isinstance(node, dict):
            return {k: self._template_for(v) for k, v in node.items()}
        if isinstance(node, list):
            # list of dict or string annot -> default []
            return []
        if self._is_string_annot(node):
            return ""
        return None

    def template(self) -> Dict[str, Any]:
        """Return zero-filled template derived from schema shape."""
        return self._template_for(self.schema)

    def _validate_node(self, node: Any, schema_node: Any, path: str, errors: List[str]) -> None:
        if isinstance(schema_node, dict):
            if not isinstance(node, dict):
                errors.append(f"{path}: expected object, got {type(node).__name__}")
                return
            for k, v in schema_node.items():
                if k not in node:
                    errors.append(f"{path}.{k}: missing")
                    continue
                self._validate_node(node.get(k), v, f"{path}.{k}", errors)
        elif isinstance(schema_node, list):
            if not isinstance(node, list):
                errors.append(f"{path}: expected array, got {type(node).__name__}")
                return
            if len(schema_node) == 0:
                return
            elem_schema = schema_node[0]
            for i, elem in enumerate(node):
                self._validate_node(elem, elem_schema, f"{path}[{i}]", errors)
        else:
            # string annotation -> expect primitive string
            if not isinstance(node, (str, type(None))):
                errors.append(f"{path}: expected string, got {type(node).__name__}")

    def validate(self, obj: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate object against schema; return (ok, errors)."""
        errors: List[str] = []
        self._validate_node(obj, self.schema, "root", errors)
        return (len(errors) == 0, errors)

    def conform(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Produce schema-shaped object, coercing missing/invalid fields."""
        def _conform(node: Any, schema_node: Any) -> Any:
            if isinstance(schema_node, dict):
                out: Dict[str, Any] = {}
                src = node if isinstance(node, dict) else {}
                for k, v in schema_node.items():
                    out[k] = _conform(src.get(k), v)
                return out
            if isinstance(schema_node, list):
                # keep only conforming elements; else empty
                src_list = node if isinstance(node, list) else []
                if not schema_node:
                    return []
                elem_schema = schema_node[0]
                res: List[Any] = []
                for elem in src_list:
                    conformed = _conform(elem, elem_schema)
                    res.append(conformed)
                return res
            # string annotation -> ensure string
            return node if isinstance(node, str) else ""
        return _conform(obj if isinstance(obj, dict) else {}, self.schema)
