import numpy as np
import pandas as pd

from gettsim.piecewise_functions import piecewise_polynomial
from gettsim.taxes.eink_st import st_tarif
from gettsim.typing import BoolSeries
from gettsim.typing import FloatSeries
from gettsim.typing import IntSeries


def lohn_st_zve(
    bruttolohn_m: FloatSeries,
    steuerklasse: IntSeries,
    eink_st_abzuege_params: dict,
    vorsorgepauschale: FloatSeries,
) -> FloatSeries:
    """Calculates taxable income (zve: zu versteuerndes Einkommen) for lohnsteuer

    Parameters
    ----------
    bruttolohn_m:
      See basic input variable :ref:`bruttolohn_m <bruttolohn_m>`.
    steuerklasse:
      See :func:`steuerklasse`
    eink_st_abzuege_params:
      See :func:`eink_st_abzuege_params`
    vorsorgepauschale
        See :func:`vorsorgepauschale`

    Returns
    -------

    """
    # WHY IS THIS 1908??
    entlastung_freibetrag_alleinerz = (steuerklasse == 2) * eink_st_abzuege_params[
        "alleinerziehenden_freibetrag"
    ]

    werbungskosten = [
        eink_st_abzuege_params["werbungskostenpauschale"] if stkl != 6 else 0
        for stkl in steuerklasse
    ]
    sonderausgaben = [
        eink_st_abzuege_params["sonderausgabenpauschbetrag"] if stkl != 6 else 0
        for stkl in steuerklasse
    ]
    # zu versteuerndes Einkommen / tax base for Lohnsteuer
    out = np.maximum(
        12 * bruttolohn_m
        - werbungskosten
        - sonderausgaben
        - entlastung_freibetrag_alleinerz
        - vorsorgepauschale,
        0,
    )

    return out


def lohn_st(
    lohn_st_zve: FloatSeries, eink_st_params: dict, steuerklasse: IntSeries
) -> FloatSeries:
    """
    Calculates Lohnsteuer = withholding tax on earnings,
    paid monthly by the employer on behalf of the employee.
    Apply the income tax tariff, but individually and with different
    exemptions, determined by the 'Steuerklasse'.
    Source: §39b EStG

    Caluclation is differentiated by steuerklasse

    1,2,4: Standard tariff (§32a (1) EStG)
    3: Splitting tariff (§32a (5) EStG)
    5,6,: Take twice the difference between applying the tariff on 5/4 and 3/4
          of taxable income. Tax rate may not be lower than the
          starting statutory one.
    Parameters
    ----------
    lohn_st_zve
        See :func:`lohn_st_zve`.
    eink_st_params
        See params documentation :ref:`eink_st_params <eink_st_params>`
    steuerklasse


    Returns
    -------
    Individual withdrawal tax on annual basis
    """
    lohnsteuer_basistarif = st_tarif(lohn_st_zve, eink_st_params)
    lohnsteuer_splittingtarif = 2 * st_tarif(lohn_st_zve / 2, eink_st_params)
    lohnsteuer_klasse5_6 = np.maximum(
        2
        * (
            st_tarif(lohn_st_zve * 1.25, eink_st_params)
            - st_tarif(lohn_st_zve * 0.75, eink_st_params)
        ),
        lohn_st_zve * eink_st_params["eink_st_tarif"]["rates"][0][1],
    )

    out = (
        (lohnsteuer_splittingtarif * (steuerklasse == 3))
        + (lohnsteuer_basistarif * (steuerklasse.isin([1, 2, 4])))
        + (lohnsteuer_klasse5_6 * (steuerklasse.isin([5, 6])))
    )

    return out


def vorsorgepauschale_ab_2010(
    bruttolohn_m: FloatSeries,
    steuerklasse: IntSeries,
    eink_st_abzuege_params: dict,
    rentenv_beitr_regular_job: FloatSeries,
    krankenv_beitr_lohnsteuer: FloatSeries,
    pflegev_beitr_regulär_beschäftigt: FloatSeries,
) -> FloatSeries:
    """
    Calculates Vorsorgepauschale for Lohnsteuer valid since 2010
    Those are deducted from gross earnings.
    Idea is similar, but not identical, to Vorsorgeaufwendungen
    used when calculating Einkommensteuer.

    Parameters
    ----------
    bruttolohn_m:
      See basic input variable :ref:`bruttolohn_m <bruttolohn_m>`.
    steuerklasse:
      See :func:`steuerklasse`
    eink_st_abzuege_params:
      See params documentation :ref:`eink_st_abzuege_params`
    pflegev_zusatz_kinderlos
      See :func:`pflegev_zusatz_kinderlos`.

    Returns
    -------
    Individual Vorsorgepauschale on annual basis
    """

    # 1. Rentenversicherungsbeiträge, §39b (2) Nr. 3a EStG.
    vorsorg_rv = (
        12
        * rentenv_beitr_regular_job
        * float(vorsorg_rv_anteil(eink_st_abzuege_params))
    )

    # 2. Krankenversicherungsbeiträge, §39b (2) Nr. 3b EStG.
    # For health care deductions, there are two ways to calculate.
    # a) at least 12% of earnings of earnings can be deducted,
    #    but only up to a certain threshold
    vorsorg_kv_option_a_basis = (
        eink_st_abzuege_params["vorsorgepauschale_mindestanteil"] * bruttolohn_m * 12
    )

    vorsorg_kv_option_a_max = np.select(
        [steuerklasse == 3, steuerklasse != 3],
        [
            eink_st_abzuege_params["vorsorgepauschale_kv_max"]["stkl3"],
            eink_st_abzuege_params["vorsorgepauschale_kv_max"]["stkl_nicht3"],
        ],
    )

    vorsorg_kv_option_a = np.minimum(vorsorg_kv_option_a_max, vorsorg_kv_option_a_basis)
    # b) Take the actual contributions (usually the better option),
    #   but apply the reduced rate!
    vorsorg_kv_option_b = krankenv_beitr_lohnsteuer
    vorsorg_kv_option_b += pflegev_beitr_regulär_beschäftigt
    # add both RV and KV deductions. For KV, take the larger amount.
    out = vorsorg_rv + np.maximum(vorsorg_kv_option_a, vorsorg_kv_option_b * 12)

    return out.fillna(0)


def vorsorgepauschale_2005_2010() -> FloatSeries:
    """
    vorsorg_rv and vorsorg_kv_option_a are identical to after 2010
    """

    out = 0
    return out


def vorsorg_rv_anteil(eink_st_abzuege_params: dict):
    """
    Calculates the share of pension contributions to be deducted for Lohnsteuer
    increases by year

    Parameters
    ----------
    eink_st_abzuege_params

    Returns
    -------
    out: float
    """

    out = piecewise_polynomial(
        x=pd.Series(eink_st_abzuege_params["datum"].year),
        thresholds=eink_st_abzuege_params["vorsorge_pauschale_rv_anteil"]["thresholds"],
        rates=eink_st_abzuege_params["vorsorge_pauschale_rv_anteil"]["rates"],
        intercepts_at_lower_thresholds=eink_st_abzuege_params[
            "vorsorge_pauschale_rv_anteil"
        ]["intercepts_at_lower_thresholds"],
    )

    return out


def steuerklasse(
    tu_id: IntSeries,
    gemeinsam_veranlagt: BoolSeries,
    alleinerziehend: BoolSeries,
    bruttolohn_m: FloatSeries,
    eink_st_params: dict,
    eink_st_abzuege_params: dict,
) -> IntSeries:
    """ Determine Lohnsteuerklassen (also called 'tax brackets')
    They determine the basic allowance for the withdrawal tax

    1: Single
    2: Single Parent
    3: One spouse in married couple who receives allowance of both partners.
       Makes sense primarily for Single-Earner Households
    4: Both spouses receive their individual allowance
    5: If one spouse chooses 3, the other has to choose 5,
       which means no allowance.
    6: Additional Job...not modelled yet, as we do not
    distinguish between different jobs

    Parameters
    ----------
    tu_id: IntSeries
        See basic input variable :ref:`tu_id <tu_id>`.
    gemeinsam_veranlagt: BoolSeries
        Return of :func:`anz_erwachsene_tu`.
    alleinerziehend: BoolSeries
        See basic input variable :ref:`alleinerziehend <alleinerziehend>`.
    bruttolohn_m: FloatSeries
        See basic input variable :ref:`bruttolohn_m <bruttolohn_m>`.
    eink_st_params:
        See params documentation :ref:`eink_st_params <eink_st_params>`
    eink_st_abzuege_params:
        See params documentation :ref:`eink_st_abzuege_params <eink_st_abzuege_params>`

    Returns
    ----------
    steuerklasse: IntSeries
        The steuerklasse for each person in the tax unit
    """

    bruttolohn_max = bruttolohn_m.groupby(tu_id).max()
    bruttolohn_min = bruttolohn_m.groupby(tu_id).min()
    # Determine Single Earner Couple:
    # If one of the spouses earns tax-free income, assume Single Earner Couple
    einkommensgrenze_zweitverdiener = (
        eink_st_params["eink_st_tarif"]["thresholds"][1]
        + eink_st_abzuege_params["werbungskostenpauschale"]
    )
    alleinverdiener_paar = (
        (bruttolohn_min <= einkommensgrenze_zweitverdiener / 12)
        & (bruttolohn_max > 0)
        & (gemeinsam_veranlagt)
    )
    cond_steuerklasse1 = (~gemeinsam_veranlagt) & ~alleinerziehend
    cond_steuerklasse2 = alleinerziehend
    cond_steuerklasse3 = alleinverdiener_paar & (
        bruttolohn_m > einkommensgrenze_zweitverdiener / 12
    )
    cond_steuerklasse4 = (gemeinsam_veranlagt) & (~alleinverdiener_paar)
    cond_steuerklasse5 = alleinverdiener_paar & (
        bruttolohn_m <= einkommensgrenze_zweitverdiener / 12
    )
    steuerklasse = (
        1 * cond_steuerklasse1
        + 2 * cond_steuerklasse2
        + 3 * cond_steuerklasse3
        + 4 * cond_steuerklasse4
        + 5 * cond_steuerklasse5
    )

    return steuerklasse
