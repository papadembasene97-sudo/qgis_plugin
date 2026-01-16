#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour appliquer les optimisations au fichier main_dock.py
"""

import re

def apply_optimizations():
    file_path = "/home/user/webapp/cheminer_indus/gui/main_dock.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Modifier le début de _visit pour initialiser l'optimiseur
    old_pattern1 = r"(    def _visit\(self\):\s+node_id = \(self\.visit_input\.text\(\) or \"\"\)\.strip\(\)\s+if not node_id:\s+QMessageBox\.information\(self\.iface\.mainWindow\(\),\"Info\",\"Saisir un ID visite\.\"\)\s+return\s+# 1\) Confirmer la pollution au nœud)"
    
    new_text1 = """    def _visit(self):
        node_id = (self.visit_input.text() or "").strip()
        if not node_id:
            QMessageBox.information(self.iface.mainWindow(),"Info","Saisir un ID visite.")
            return

        # Initialiser l'optimiseur si nécessaire et construire les caches
        if not self._node_ops:
            self._node_ops = OptimizedNodeOps(
                self.canal_layer, self.fosse_layer, 
                self.liaison_layer, self.indus_layer
            )
        else:
            # Mettre à jour les couches au cas où elles auraient changé
            self._node_ops.canal_layer = self.canal_layer
            self._node_ops.fosse_layer = self.fosse_layer
            self._node_ops.liaison_layer = self.liaison_layer
            self._node_ops.indus_layer = self.indus_layer
            # Invalider les caches pour refléter les changements
            self._node_ops.invalidate_caches()

        # 1) Confirmer la pollution au nœud"""
    
    content = re.sub(old_pattern1, new_text1, content, flags=re.DOTALL)
    
    # 2. Remplacer _bulk_deselect_unselected_branches par version optimisée
    content = content.replace(
        "removed_indus_up = self._bulk_deselect_unselected_branches(node_id, branches, chosen_keep)",
        "removed_indus_up = self._node_ops.bulk_deselect_unselected_branches_optimized(node_id, branches, chosen_keep)"
    )
    
    content = content.replace(
        "removed_indus_up = self._bulk_deselect_unselected_branches(node_id, branches, chosen_ids=set())",
        "removed_indus_up = self._node_ops.bulk_deselect_unselected_branches_optimized(node_id, branches, chosen_ids=set())"
    )
    
    # 3. Remplacer _walk_downstream_on_selected par version optimisée
    old_walk_down = """            # 5.a Désélectionner l'AVAL de ce nœud (sur la sélection courante)
            cids_ds, fids_ds, nodes_ds = self._walk_downstream_on_selected(node_id)"""
    
    new_walk_down = """            # 5.a Désélectionner l'AVAL de ce nœud (sur la sélection courante) - VERSION OPTIMISÉE
            sel_c, sel_f = self._selected_id_sets()
            cids_ds, fids_ds, nodes_ds = self._node_ops.walk_downstream_on_selected_optimized(node_id, sel_c, sel_f)"""
    
    content = content.replace(old_walk_down, new_walk_down)
    
    # 4. Remplacer _deselect_liaisons_and_indus_from_nodes par version optimisée
    content = content.replace(
        "removed_indus_down = self._deselect_liaisons_and_indus_from_nodes(nodes_ds)",
        "removed_indus_down = self._node_ops.deselect_liaisons_and_indus_from_nodes_optimized(nodes_ds)"
    )
    
    # 5. Remplacer _walk_upstream_on_selected par version optimisée
    old_walk_up = """                # Remonter sur la sélection à partir de l'amont de la branche cochée
                if amont:
                    kc, kf, kn = self._walk_upstream_on_selected(amont)"""
    
    new_walk_up = """                # Remonter sur la sélection à partir de l'amont de la branche cochée - VERSION OPTIMISÉE
                if amont:
                    sel_c, sel_f = self._selected_id_sets()
                    kc, kf, kn = self._node_ops.walk_upstream_on_selected_optimized(amont, sel_c, sel_f)"""
    
    content = content.replace(old_walk_up, new_walk_up)
    
    # 6. Remplacer le second appel à _deselect_liaisons_and_indus_from_nodes
    old_deselect2 = """            if nodes_removed:
                removed_indus_down.update(self._deselect_liaisons_and_indus_from_nodes(nodes_removed))"""
    
    new_deselect2 = """            if nodes_removed:
                removed_indus_down.update(self._node_ops.deselect_liaisons_and_indus_from_nodes_optimized(nodes_removed))"""
    
    content = content.replace(old_deselect2, new_deselect2)
    
    # Écrire le fichier modifié
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Optimisations appliquées avec succès à main_dock.py")
    return True

if __name__ == "__main__":
    apply_optimizations()
