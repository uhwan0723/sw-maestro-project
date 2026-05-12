package com.soma2026.tikitalka.domain.repository

import com.soma2026.tikitalka.domain.model.Issue
import com.soma2026.tikitalka.domain.model.PagedResult

interface IssueRepository {
    suspend fun getIssues(
        tag: String?,
        page: Int,
        size: Int,
        sort: String,
    ): Result<PagedResult<Issue>>

    suspend fun getIssueDetail(id: String): Result<Issue>
}