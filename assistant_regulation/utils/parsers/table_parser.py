"""
Module de parsing des tableaux pour l'affichage
"""
import pandas as pd
from typing import List, Dict, Any, Optional, Union


class TableParser:
    """Classe pour parser et formater les tableaux"""
    
    @staticmethod
    def fix_column_names(columns: Optional[List[str]]) -> List[str]:
        """
        Corrige les noms de colonnes dupliqués ou invalides
        
        Args:
            columns: Liste des noms de colonnes à corriger
            
        Returns:
            Liste des noms de colonnes corrigés
        """
        if columns is None:
            return [f"Col_{i}" for i in range(20)]  # Noms génériques
        
        # Assurer que nous avons une liste
        cols = list(columns)
        
        # Remplacer les None par des noms génériques
        for i in range(len(cols)):
            if cols[i] is None or cols[i] == "":
                cols[i] = f"Col_{i}"
        
        # Gérer les doublons en ajoutant _1, _2, etc.
        seen = {}
        for i in range(len(cols)):
            if cols[i] in seen:
                seen[cols[i]] += 1
                cols[i] = f"{cols[i]}_{seen[cols[i]]}"
            else:
                seen[cols[i]] = 0
        
        return cols
    
    @staticmethod
    def parse_matrix_data(content: List[List[Any]]) -> Optional[pd.DataFrame]:
        """
        Parse les données sous forme de matrice (liste de listes)
        
        Args:
            content: Données sous forme de matrice
            
        Returns:
            DataFrame pandas ou None si échec
        """
        if not content or len(content) == 0:
            return None
        
        try:
            # Corriger les noms de colonnes
            column_names = TableParser.fix_column_names(content[0] if len(content) > 0 else None)
            df = pd.DataFrame(content[1:], columns=column_names)
            return df
        except Exception:
            return None
    
    @staticmethod
    def parse_dict_list_data(content: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
        """
        Parse les données sous forme de liste de dictionnaires
        
        Args:
            content: Données sous forme de liste de dictionnaires
            
        Returns:
            DataFrame pandas ou None si échec
        """
        try:
            df = pd.DataFrame(content)
            return df
        except Exception:
            return None
    
    @staticmethod
    def parse_delimited_text(content: str) -> Optional[pd.DataFrame]:
        """
        Parse un texte délimité (pipes, tabs, etc.)
        
        Args:
            content: Texte contenant un tableau délimité
            
        Returns:
            DataFrame pandas ou None si échec
        """
        try:
            # Rechercher des patterns qui ressemblent à des tableaux
            if '|' not in content and '\t' not in content:
                return None
            
            # Tentative de splitting et nettoyage
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            if not lines:
                return None
            
            rows = []
            for line in lines:
                if '|' in line:
                    cells = [cell.strip() for cell in line.split('|')]
                else:
                    cells = [cell.strip() for cell in line.split('\t')]
                rows.append(cells)
            
            if not rows or len(rows) == 0:
                return None
            
            # Corriger les noms de colonnes
            column_names = TableParser.fix_column_names(rows[0] if len(rows) > 0 else None)
            df = pd.DataFrame(rows[1:], columns=column_names)
            return df
        except Exception:
            return None
    
    @staticmethod
    def parse_table_content(content: Union[str, List, Dict]) -> Optional[pd.DataFrame]:
        """
        Parse le contenu d'un tableau selon son format
        
        Args:
            content: Contenu du tableau à parser
            
        Returns:
            DataFrame pandas ou None si impossible à parser
        """
        # Cas 1: Matrice (liste de listes)
        if isinstance(content, list) and all(isinstance(row, list) for row in content):
            return TableParser.parse_matrix_data(content)
        
        # Cas 2: Liste de dictionnaires
        if isinstance(content, list) and all(isinstance(row, dict) for row in content):
            return TableParser.parse_dict_list_data(content)
        
        # Cas 3: Texte délimité
        if isinstance(content, str):
            return TableParser.parse_delimited_text(content)
        
        return None
    
    @staticmethod
    def extract_table_stats(tables: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Extrait les statistiques des tableaux
        
        Args:
            tables: Liste des tableaux
            
        Returns:
            Dictionnaire avec les statistiques
        """
        return {
            "total": len(tables),
            "parseable": sum(1 for table in tables if TableParser.parse_table_content(table.get('documents', "")) is not None)
        }