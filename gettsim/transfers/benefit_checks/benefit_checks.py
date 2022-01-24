from gettsim.typing import BoolSeries
from gettsim.typing import FloatSeries


def arbeitsl_geld_2_m_minus_eink_hh(
    regelbedarf_m_vermögens_check_hh: FloatSeries,
    kindergeld_m_hh: FloatSeries,
    unterhaltsvors_m_hh: FloatSeries,
    arbeitsl_geld_2_eink_hh: FloatSeries,
) -> FloatSeries:
    """Calculate remaining basic subsistence after recieving other benefits.

    Parameters
    ----------
    regelbedarf_m_vermögens_check_hh
        See :func:`regelbedarf_m_vermögens_check_hh`.
    kindergeld_m_hh
        See :func:`kindergeld_m_hh`.
    unterhaltsvors_m_hh
        See :func:`unterhaltsvors_m_hh`.
    arbeitsl_geld_2_eink_hh
        See :func:`arbeitsl_geld_2_eink_hh`.

    Returns
    -------

    """
    out = (
        regelbedarf_m_vermögens_check_hh
        - arbeitsl_geld_2_eink_hh
        - unterhaltsvors_m_hh
        - kindergeld_m_hh
    )
    return out.clip(lower=0)


def wohngeld_vorrang_hh(
    wohngeld_vermögens_check_hh: FloatSeries,
    arbeitsl_geld_2_m_minus_eink_hh: FloatSeries,
) -> BoolSeries:
    """Check if housing benefit has priority.

    Parameters
    ----------
    wohngeld_vermögens_check_hh
        See :func:`wohngeld_vermögens_check_hh`.
    arbeitsl_geld_2_m_minus_eink_hh
        See :func:`arbeitsl_geld_2_m_minus_eink_hh`.

    Returns
    -------

    """
    return wohngeld_vermögens_check_hh >= arbeitsl_geld_2_m_minus_eink_hh


def kinderzuschl_vorrang_hh(
    kinderzuschl_vermögens_check_hh: FloatSeries,
    arbeitsl_geld_2_m_minus_eink_hh: FloatSeries,
) -> BoolSeries:
    """Check if child benefit has priority.

    Parameters
    ----------
    kinderzuschl_vermögens_check_hh
        See :func:`kinderzuschl_vermögens_check_hh`.
    arbeitsl_geld_2_m_minus_eink_hh
        See :func:`arbeitsl_geld_2_m_minus_eink_hh`.

    Returns
    -------

    """
    return kinderzuschl_vermögens_check_hh >= arbeitsl_geld_2_m_minus_eink_hh


def wohngeld_kinderzuschl_vorrang_hh(
    wohngeld_vermögens_check_hh: FloatSeries,
    kinderzuschl_vermögens_check_hh: FloatSeries,
    arbeitsl_geld_2_m_minus_eink_hh: FloatSeries,
) -> BoolSeries:
    """Check if housing and child benefit have priority.

    Parameters
    ----------
    wohngeld_vermögens_check_hh
        See :func:`wohngeld_vermögens_check_hh`.
    kinderzuschl_vermögens_check_hh
        See :func:`kinderzuschl_vermögens_check_hh`.
    arbeitsl_geld_2_m_minus_eink_hh
        See :func:`arbeitsl_geld_2_m_minus_eink_hh`.

    Returns
    -------

    """
    sum_wohngeld_kinderzuschl = (
        wohngeld_vermögens_check_hh + kinderzuschl_vermögens_check_hh
    )
    return sum_wohngeld_kinderzuschl >= arbeitsl_geld_2_m_minus_eink_hh
