# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, time
from typing import Any, Dict

class AutoSaver:
    """
    Sauvegarde continue du contexte dans un fichier .txt (JSONL).
    - log_event(name, payload) : append
    - dump_state(state_dict) : remplace le snapshot courant (state.json)
    - load_state() : recharge le snapshot si dispo
    """
    def __init__(self, work_dir: str):
        self.dir = work_dir
        os.makedirs(self.dir, exist_ok=True)
        self.stream_path = os.path.join(self.dir, "autosave.txt")
        self.state_path  = os.path.join(self.dir, "state.json")

    def log_event(self, name: str, payload: Dict[str, Any]):
        rec = {"ts": time.time(), "event": name, "data": payload}
        with open(self.stream_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def dump_state(self, state: Dict[str, Any]):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self) -> Dict[str, Any]:
        if not os.path.exists(self.state_path):
            return {}
        with open(self.state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def reset(self):
        for p in (self.stream_path, self.state_path):
            try:
                if os.path.exists(p): os.remove(p)
            except Exception:
                pass
