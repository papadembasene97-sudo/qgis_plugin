# -*- coding: utf-8 -*-
"""
Générateur de rapports PDF pour les PV non conformes - CheminerIndus
Génère des rapports d'enquête de pollution originés depuis un PV non conforme
"""

from __future__ import annotations
import os
from typing import Dict, Any, List, Optional
from .pdf_generator import PDFGenerator


class PVReportGenerator:
    """Générateur de rapports PDF pour les PV non conformes"""
    
    def __init__(self, logo_path: str = "", legend_path: str = ""):
        self.logo_path = logo_path
        self.legend_path = legend_path
        
    def generate_pollution_report(
        self,
        polluter_info: Dict[str, Any],
        path_data: Dict[str, Any],
        output_path: str
    ) -> bool:
        """
        Génère un rapport d'enquête de pollution depuis un PV non conforme
        
        Args:
            polluter_info: Informations sur le PV pollueur (depuis PVAnalyzer.get_polluter_info())
            path_data: Données du cheminement Amont→Aval
            output_path: Chemin du fichier PDF à générer
            
        Returns:
            True si réussi, False sinon
        """
        try:
            pdf = PDFGenerator(self.logo_path, self.legend_path)
            pdf.alias_nb_pages()
            pdf.add_page()
            
            # En-tête du rapport
            pdf.set_global_header("RAPPORT D'ENQUÊTE DE POLLUTION - CheminerIndus v1.2.3")
            pdf.set_title_top("RAPPORT D'ENQUÊTE DE POLLUTION")
            
            # Vérifier le type d'origine
            is_pv_polluter = polluter_info.get('type') == 'PV'
            
            # Section 1: Origine de la pollution
            self._add_origin_section(pdf, polluter_info, is_pv_polluter)
            
            # Section 2: Parcours Amont → Aval
            self._add_path_section(pdf, path_data)
            
            # Section 3: Photos Street View
            self._add_photos_section(pdf, path_data)
            
            # Section 4: Autres PV sur le parcours
            if is_pv_polluter:
                self._add_other_pv_section(pdf, path_data)
            
            # Section 5: Industriels sur le parcours
            self._add_industriels_section(pdf, path_data)
            
            # Section 6: Recommandations
            self._add_recommendations_section(pdf, polluter_info, is_pv_polluter)
            
            # Sauvegarder le PDF
            pdf.output(output_path)
            return True
            
        except Exception as e:
            print(f"Erreur lors de la génération du rapport PDF: {e}")
            return False
            
    def _add_origin_section(self, pdf: PDFGenerator, polluter_info: Dict[str, Any], is_pv: bool):
        """Ajoute la section Origine de la pollution"""
        pdf.section_title("1. ORIGINE DE LA POLLUTION")
        
        if is_pv:
            # Origine : PV non conforme
            pdf._set_font_bold(pdf.FONT_BASE + 1)
            pdf.cell(0, 7, "🏠 Point de branchement non conforme (PV)", ln=True)
            pdf._set_font_base()
            
            rows = [
                ("N° PV", polluter_info.get('num_pv', 'N/A')),
                ("Adresse", polluter_info.get('adresse', 'N/A')),
                ("Commune", polluter_info.get('commune', 'N/A')),
                ("Conforme", polluter_info.get('conforme', 'N/A')),
                ("", ""),
                ("Non-conformités détectées", ""),
            ]
            
            # Ajouter les non-conformités
            eu_vers_ep = polluter_info.get('eu_vers_ep', 'Non')
            ep_vers_eu = polluter_info.get('ep_vers_eu', 'Non')
            
            if eu_vers_ep == 'Oui':
                rows.append(("  → EU vers EP", "⚠️ OUI"))
            else:
                rows.append(("  → EU vers EP", "Non"))
                
            if ep_vers_eu == 'Oui':
                rows.append(("  → EP vers EU", "⚠️ OUI"))
            else:
                rows.append(("  → EP vers EU", "Non"))
            
            rows.extend([
                ("", ""),
                ("Date du contrôle", polluter_info.get('date_controle', 'N/A')),
                ("Nombre de chambres", str(polluter_info.get('nb_chambres', 'N/A'))),
                ("Surface EP (m²)", str(polluter_info.get('surf_ep', 'N/A'))),
            ])
            
            # Lien OSMOSE
            lien_osmose = polluter_info.get('lien_osmose', '')
            if lien_osmose:
                rows.append(("Lien OSMOSE", lien_osmose))
            
            pdf._kv_table(rows)
            
        else:
            # Origine : Industriel
            pdf._set_font_bold(pdf.FONT_BASE + 1)
            pdf.cell(0, 7, "🏭 Industriel", ln=True)
            pdf._set_font_base()
            
            rows = [
                ("Nom", polluter_info.get('nom', 'N/A')),
                ("Type", polluter_info.get('type', 'N/A')),
                ("Adresse", polluter_info.get('adresse', 'N/A')),
                ("Commune", polluter_info.get('commune', 'N/A')),
            ]
            
            pdf._kv_table(rows)
        
        pdf.ln(5)
        
    def _add_path_section(self, pdf: PDFGenerator, path_data: Dict[str, Any]):
        """Ajoute la section Parcours"""
        pdf.section_title("2. PARCOURS AMONT → AVAL")
        
        # Statistiques du parcours
        rows = [
            ("Distance totale", f"{path_data.get('distance_total', 0):.1f} m"),
            ("Nombre de canalisations", str(path_data.get('nb_canalisations', 0))),
            ("Nombre de nœuds", str(path_data.get('nb_noeuds', 0))),
            ("Ouvrage d'arrivée", path_data.get('ouvrage_arrivee', 'N/A')),
        ]
        
        pdf._kv_table(rows)
        pdf.ln(3)
        
        # Détails du parcours (si disponible)
        if 'canalisations' in path_data and path_data['canalisations']:
            pdf.sub_section("Détails du cheminement")
            
            canals = path_data['canalisations']
            max_display = 20  # Limiter l'affichage à 20 canalisations
            
            for i, canal in enumerate(canals[:max_display]):
                canal_id = canal.get('id', 'N/A')
                longueur = canal.get('longueur', 0)
                type_reseau = canal.get('type_reseau', 'N/A')
                
                pdf._set_font_base()
                pdf.cell(0, 5, f"  {i+1}. Canal {canal_id} - {longueur:.1f}m - {type_reseau}", ln=True)
            
            if len(canals) > max_display:
                pdf._set_font_small()
                pdf.cell(0, 5, f"  ... et {len(canals) - max_display} autres canalisations", ln=True)
                pdf._set_font_base()
        
        pdf.ln(5)
        
    def _add_photos_section(self, pdf: PDFGenerator, path_data: Dict[str, Any]):
        """Ajoute la section Photos Street View"""
        pdf.section_title("3. PHOTOS STREET VIEW")
        
        if 'photos' in path_data and path_data['photos']:
            photos = path_data['photos']
            
            for i, photo in enumerate(photos[:4]):  # Max 4 photos
                photo_path = photo.get('path', '')
                description = photo.get('description', f'Photo {i+1}')
                
                if os.path.exists(photo_path):
                    pdf.sub_section(description)
                    
                    # Ajouter l'image
                    try:
                        img_w = 160  # Largeur de l'image en mm
                        pdf.image(photo_path, x=pdf.l_margin, y=None, w=img_w)
                        pdf.ln(3)
                    except Exception as e:
                        pdf._set_font_small()
                        pdf.cell(0, 5, f"[Erreur de chargement de l'image: {e}]", ln=True)
                        pdf._set_font_base()
        else:
            pdf._set_font_small()
            pdf.cell(0, 5, "Aucune photo disponible.", ln=True)
            pdf._set_font_base()
        
        pdf.ln(5)
        
    def _add_other_pv_section(self, pdf: PDFGenerator, path_data: Dict[str, Any]):
        """Ajoute la section Autres PV sur le parcours"""
        pdf.section_title("4. AUTRES PV NON CONFORMES SUR LE PARCOURS")
        
        if 'pv_list' in path_data and path_data['pv_list']:
            pv_list = path_data['pv_list']
            
            pdf._set_font_base()
            pdf.cell(0, 5, f"Nombre de PV non conformes détectés : {len(pv_list)}", ln=True)
            pdf.ln(2)
            
            for i, pv in enumerate(pv_list[:10]):  # Max 10 PV
                num_pv = pv.get('num_pv', 'N/A')
                adresse = pv.get('adresse', 'N/A')
                commune = pv.get('commune', 'N/A')
                eu_vers_ep = pv.get('eu_vers_ep', 'Non')
                ep_vers_eu = pv.get('ep_vers_eu', 'Non')
                
                # Icône selon les non-conformités
                icon = "⚠️" if (eu_vers_ep == 'Oui' or ep_vers_eu == 'Oui') else "🏠"
                
                pdf._set_font_base()
                pdf.cell(0, 5, f"{icon} PV n°{num_pv} - {adresse}, {commune}", ln=True)
                
                # Afficher les non-conformités
                if eu_vers_ep == 'Oui' or ep_vers_eu == 'Oui':
                    pdf._set_font_small()
                    if eu_vers_ep == 'Oui':
                        pdf.cell(0, 4, "    → Inversion EU vers EP détectée", ln=True)
                    if ep_vers_eu == 'Oui':
                        pdf.cell(0, 4, "    → Inversion EP vers EU détectée", ln=True)
                    pdf._set_font_base()
            
            if len(pv_list) > 10:
                pdf._set_font_small()
                pdf.cell(0, 5, f"... et {len(pv_list) - 10} autres PV non conformes", ln=True)
                pdf._set_font_base()
        else:
            pdf._set_font_small()
            pdf.cell(0, 5, "Aucun autre PV non conforme détecté sur le parcours.", ln=True)
            pdf._set_font_base()
        
        pdf.ln(5)
        
    def _add_industriels_section(self, pdf: PDFGenerator, path_data: Dict[str, Any]):
        """Ajoute la section Industriels sur le parcours"""
        pdf.section_title("5. INDUSTRIELS SUR LE PARCOURS")
        
        if 'industriels' in path_data and path_data['industriels']:
            industriels = path_data['industriels']
            
            pdf._set_font_base()
            pdf.cell(0, 5, f"Nombre d'industriels détectés : {len(industriels)}", ln=True)
            pdf.ln(2)
            
            for i, indus in enumerate(industriels[:10]):  # Max 10 industriels
                nom = indus.get('nom', 'N/A')
                type_indus = indus.get('type', 'N/A')
                adresse = indus.get('adresse', 'N/A')
                commune = indus.get('commune', 'N/A')
                
                pdf._set_font_base()
                pdf.cell(0, 5, f"🏭 {nom} ({type_indus})", ln=True)
                pdf._set_font_small()
                pdf.cell(0, 4, f"    {adresse}, {commune}", ln=True)
                pdf._set_font_base()
                pdf.ln(1)
            
            if len(industriels) > 10:
                pdf._set_font_small()
                pdf.cell(0, 5, f"... et {len(industriels) - 10} autres industriels", ln=True)
                pdf._set_font_base()
        else:
            pdf._set_font_small()
            pdf.cell(0, 5, "Aucun industriel détecté sur le parcours.", ln=True)
            pdf._set_font_base()
        
        pdf.ln(5)
        
    def _add_recommendations_section(
        self,
        pdf: PDFGenerator,
        polluter_info: Dict[str, Any],
        is_pv: bool
    ):
        """Ajoute la section Recommandations"""
        pdf.section_title("6. RECOMMANDATIONS")
        
        if is_pv:
            # Recommandations pour PV non conforme
            eu_vers_ep = polluter_info.get('eu_vers_ep', 'Non')
            ep_vers_eu = polluter_info.get('ep_vers_eu', 'Non')
            
            pdf._set_font_base()
            
            if eu_vers_ep == 'Oui':
                pdf.cell(0, 6, "⚠️ Inversion EU vers EP détectée", ln=True)
                pdf._set_font_small()
                pdf.multi_cell(
                    0, 4,
                    "   → Il est recommandé de procéder à une visite terrain pour vérifier "
                    "le branchement et corriger l'inversion. Les eaux usées domestiques "
                    "ne doivent pas se déverser dans le réseau pluvial."
                )
                pdf.ln(2)
                pdf._set_font_base()
            
            if ep_vers_eu == 'Oui':
                pdf.cell(0, 6, "⚠️ Inversion EP vers EU détectée", ln=True)
                pdf._set_font_small()
                pdf.multi_cell(
                    0, 4,
                    "   → Il est recommandé de procéder à une visite terrain pour vérifier "
                    "le branchement et corriger l'inversion. Les eaux pluviales "
                    "ne doivent pas se déverser dans le réseau d'eaux usées."
                )
                pdf.ln(2)
                pdf._set_font_base()
            
            if eu_vers_ep == 'Non' and ep_vers_eu == 'Non':
                pdf._set_font_small()
                pdf.multi_cell(
                    0, 4,
                    "Aucune inversion majeure détectée, mais une visite de contrôle "
                    "est recommandée pour confirmer la conformité du branchement."
                )
                pdf._set_font_base()
            
            # Actions suggérées
            pdf.ln(3)
            pdf.sub_section("Actions suggérées")
            pdf._set_font_small()
            pdf.cell(0, 5, "1. Visite terrain du PV pour contrôle visuel", ln=True)
            pdf.cell(0, 5, "2. Vérification de la conformité du branchement", ln=True)
            pdf.cell(0, 5, "3. Correction des inversions si nécessaire", ln=True)
            pdf.cell(0, 5, "4. Mise à jour du statut dans OSMOSE", ln=True)
            pdf.cell(0, 5, "5. Nouveau contrôle après travaux", ln=True)
            
        else:
            # Recommandations pour industriel
            pdf._set_font_small()
            pdf.multi_cell(
                0, 4,
                "Un industriel a été identifié comme origine probable de la pollution. "
                "Il est recommandé de :\n\n"
                "1. Contacter l'industriel pour enquête\n"
                "2. Vérifier les installations de pré-traitement\n"
                "3. Contrôler les rejets et leur conformité\n"
                "4. Procéder à des prélèvements si nécessaire\n"
                "5. Mettre en demeure si non-conformité avérée"
            )
        
        pdf._set_font_base()
