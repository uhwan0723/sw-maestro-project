package com.soma2026.tikitalka.domain.model

data class PagedResult<T>(
    val content: List<T>,
    val page: Int,
    val size: Int,
    val totalElements: Int,
    val totalPages: Int,
)