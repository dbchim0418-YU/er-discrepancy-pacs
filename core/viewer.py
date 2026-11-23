"""기본 뷰어. 주인: 채민

show_image()는 uint8 배열을 받아 화면에 보여준다.
- 확대·축소: 마우스 휠 / 이동: 드래그 / 초기화: 더블클릭 또는 '화면 초기화' 버튼
- compare를 주면 원본과 결과를 나란히 보여준다(주연이 처리 결과 비교에 사용).
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import plotly.express as px
import streamlit as st

_PLOT_CONFIG = {
    "scrollZoom": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "toImage"],
}


def _figure(image: np.ndarray, title: str):
    fig = px.imshow(image, color_continuous_scale="gray", zmin=0, zmax=255)
    fig.update_layout(
        title=title,
        dragmode="pan",
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=40 if title else 0, b=0),
    )
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    return fig


def _check_gray_uint8(image: np.ndarray, name: str) -> None:
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 2:
        raise ValueError(f"{name}은(는) 흑백 uint8 2차원 배열이어야 합니다.")


def validate_images(image: np.ndarray, compare: Optional[np.ndarray] = None) -> None:
    """뷰어에 넣기 전 영상 형식 검사(개발 규칙 2번).

    알고리즘이 잘못된 결과를 넘기면 화면에 그려지기 전에 원인을 알려준다.
    """
    _check_gray_uint8(image, "원본 영상")
    if compare is not None:
        _check_gray_uint8(compare, "처리 결과 영상")
        if compare.shape != image.shape:
            raise ValueError(
                f"처리 결과 영상의 크기 {compare.shape}가 원본 {image.shape}과 다릅니다. "
                "알고리즘은 입력과 같은 크기를 돌려줘야 합니다."
            )


def show_image(
    image: np.ndarray,
    key: str,
    compare: Optional[np.ndarray] = None,
    titles: tuple[str, str] = ("원본", "처리 결과"),
) -> None:
    """영상 표시. key는 화면마다 겹치지 않게 접두어를 붙인다(예: img_case_view)."""
    validate_images(image, compare)

    reset_key = f"img_reset_{key}"
    if st.button("화면 초기화", key=f"{key}_reset_btn"):
        st.session_state[reset_key] = st.session_state.get(reset_key, 0) + 1
    version = st.session_state.get(reset_key, 0)

    if compare is None:
        st.plotly_chart(_figure(image, ""), config=_PLOT_CONFIG, key=f"{key}_{version}")
        return

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_figure(image, titles[0]), config=_PLOT_CONFIG, key=f"{key}_a_{version}")
    with right:
        st.plotly_chart(_figure(compare, titles[1]), config=_PLOT_CONFIG, key=f"{key}_b_{version}")
