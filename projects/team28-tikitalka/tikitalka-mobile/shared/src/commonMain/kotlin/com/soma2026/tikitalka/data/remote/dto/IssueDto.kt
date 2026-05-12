package com.soma2026.tikitalka.data.remote.dto

import com.soma2026.tikitalka.domain.model.Issue
import kotlinx.serialization.Serializable

@Serializable
data class IssueDto(
    val id: String,
    val title: String,
    val summary: String,
    val tag: String,
    val publishedAt: String,
    val hotnessScore: Int,
    val url: String,
    val source: String,
    val originalContent: String? = null,
)

fun IssueDto.toDomain(): Issue = Issue(
    id = id,
    title = title,
    summary = summary,
    tag = tag,
    publishedAt = publishedAt,
    hotnessScore = hotnessScore,
    url = url,
    source = source,
    originalContent = originalContent,
)

