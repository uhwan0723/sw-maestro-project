package com.soma2026.tikitalka.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class PagedIssueDto(
    val content: List<IssueDto>,
    val page: Int,
    val size: Int,
    val totalElements: Int,
    val totalPages: Int,
)