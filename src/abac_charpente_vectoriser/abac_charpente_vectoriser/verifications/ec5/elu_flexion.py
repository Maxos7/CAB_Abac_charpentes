"""
verifications.ec5.elu_flexion
=============================
Vérifications ELU de flexion — EC5 §6.1.6.

Trois vérifications :
- ``FlexionSimple``      : taux σ_m,y / (k_crit × f_m,d) ≤ 1  (Eq. 6.11)
- ``DoubleFlexionForte`` : Eq. (6.19) — condition déterminante axe fort
- ``DoubleFlexionFaible``: Eq. (6.20) — condition déterminante axe faible

La double flexion n'est active que si ``EspaceCombinaisonTenseur.M_y_kNm`` et
``M_z_kNm`` sont non ``None`` (ce qui est le cas si ``TypePoutreVect.double_flexion_active``).

Le coefficient k_m = 0.7 (section rectangulaire, EC5 §6.1.6(2)) est lu depuis
``donnees/params_ec5.csv`` via le module ``ec5.proprietes``.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

import numpy as np
import pandas as pd

from ...protocoles.verification import ResultatVerification, VerificationELU


@lru_cache(maxsize=1)
def _k_m() -> float:
    """Lit le coefficient k_m depuis params_ec5.csv — EC5 §6.1.6(2)."""
    chemin: str = str(files("abac_charpente_vectoriser.donnees").joinpath("params_ec5.csv"))
    df: pd.DataFrame = pd.read_csv(chemin, sep=";", comment="#")
    return float(df.set_index("parametre").loc["k_m", "valeur"])


class FlexionSimple(VerificationELU):
    """Flexion simple — EC5 §6.1.6 Eq.(6.11).

    σ_m,y,d / (k_crit × f_m,d) ≤ 1.0
    """

    @property
    def id_verification(self) -> str:
        return "FlexionSimple"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.1.6 Eq.(6.11)"

    def calculer(self, espace) -> ResultatVerification:
        """Calcule le taux de flexion simple.

        σ_m,y,d = M_d / W_y   [MPa]
        Taux = σ_m,y,d / (k_crit × f_m,d)

        Shapes :
            M_d_kNm  : (n_L, n_C, n_M)
            W_y_cm3  : (n_M,)  → (1, 1, n_M)
            k_crit   : (n_L, n_M) → (n_L, 1, n_M)
            f_m_d_CM : (n_C, n_M) → (1, n_C, n_M)
        """
        # M en kN·m → σ en MPa : (kN·m) / (cm³) × 1e3 = MPa
        W_y: np.ndarray = espace.W_y_cm3_arr[np.newaxis, np.newaxis, :]        # (1, 1, n_M)
        sigma_m_y: np.ndarray = espace.M_d_kNm / W_y * 1e3                    # (n_L, n_C, n_M) [MPa]

        k_crit: np.ndarray = espace.k_crit_LM[:, np.newaxis, :]               # (n_L, 1, n_M)
        f_m_d: np.ndarray = espace.f_m_d_CM[np.newaxis, :, :]                 # (1, n_C, n_M)

        taux: np.ndarray = sigma_m_y / (k_crit * f_m_d)
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)


class DoubleFlexionForte(VerificationELU):
    """Double flexion — condition déterminante axe fort — EC5 §6.1.6 Eq.(6.19).

    σ_m,y,d / (k_crit × f_m,d) + k_m × σ_m,z,d / f_m,d ≤ 1.0
    """

    @property
    def id_verification(self) -> str:
        return "DoubleFlexionForte"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.1.6 Eq.(6.19)"

    def calculer(self, espace) -> ResultatVerification:
        """Active uniquement si ``M_y_kNm`` et ``M_z_kNm`` sont non None."""
        if espace.M_y_kNm is None or espace.M_z_kNm is None:
            n_L, n_C, n_M = espace.M_d_kNm.shape
            zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
            active: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
            return ResultatVerification(self.id_verification, zeros, active)

        km: float = _k_m()
        W_y: np.ndarray = espace.W_y_cm3_arr[np.newaxis, np.newaxis, :]
        W_z: np.ndarray = espace.W_z_cm3_arr[np.newaxis, np.newaxis, :]
        k_crit: np.ndarray = espace.k_crit_LM[:, np.newaxis, :]
        f_m_d: np.ndarray = espace.f_m_d_CM[np.newaxis, :, :]

        sigma_y: np.ndarray = espace.M_y_kNm / W_y * 1e3   # (n_L, n_C, n_M) [MPa]
        sigma_z: np.ndarray = espace.M_z_kNm / W_z * 1e3   # (n_L, n_C, n_M) [MPa]

        taux: np.ndarray = sigma_y / (k_crit * f_m_d) + km * sigma_z / f_m_d
        active = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)


class DoubleFlexionFaible(VerificationELU):
    """Double flexion — condition déterminante axe faible — EC5 §6.1.6 Eq.(6.20).

    k_m × σ_m,y,d / (k_crit × f_m,d) + σ_m,z,d / f_m,d ≤ 1.0
    """

    @property
    def id_verification(self) -> str:
        return "DoubleFlexionFaible"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.1.6 Eq.(6.20)"

    def calculer(self, espace) -> ResultatVerification:
        """Active uniquement si ``M_y_kNm`` et ``M_z_kNm`` sont non None."""
        if espace.M_y_kNm is None or espace.M_z_kNm is None:
            n_L, n_C, n_M = espace.M_d_kNm.shape
            zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
            active: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
            return ResultatVerification(self.id_verification, zeros, active)

        km: float = _k_m()
        W_y: np.ndarray = espace.W_y_cm3_arr[np.newaxis, np.newaxis, :]
        W_z: np.ndarray = espace.W_z_cm3_arr[np.newaxis, np.newaxis, :]
        k_crit: np.ndarray = espace.k_crit_LM[:, np.newaxis, :]
        f_m_d: np.ndarray = espace.f_m_d_CM[np.newaxis, :, :]

        sigma_y: np.ndarray = espace.M_y_kNm / W_y * 1e3
        sigma_z: np.ndarray = espace.M_z_kNm / W_z * 1e3

        taux: np.ndarray = km * sigma_y / (k_crit * f_m_d) + sigma_z / f_m_d
        active = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)
