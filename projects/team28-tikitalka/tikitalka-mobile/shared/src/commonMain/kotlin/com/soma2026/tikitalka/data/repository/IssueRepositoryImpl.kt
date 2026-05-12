package com.soma2026.tikitalka.data.repository

import com.soma2026.tikitalka.data.remote.api.IssueApi
import com.soma2026.tikitalka.data.remote.dto.toDomain
import com.soma2026.tikitalka.domain.model.Issue
import com.soma2026.tikitalka.domain.model.PagedResult
import com.soma2026.tikitalka.domain.repository.IssueRepository

class IssueRepositoryImpl(
    private val api: IssueApi,
) : IssueRepository {

    override suspend fun getIssues(
        tag: String?,
        page: Int,
        size: Int,
        sort: String,
    ): Result<PagedResult<Issue>> = runCatching {
        val response = api.getIssues(tag, page, size, sort)
        PagedResult(
            content = response.content.map { it.toDomain() },
            page = response.page,
            size = response.size,
            totalElements = response.totalElements,
            totalPages = response.totalPages,
        )
    }

    override suspend fun getIssueDetail(id: String): Result<Issue> = runCatching {
        api.getIssueDetail(id).toDomain()
    }
}
