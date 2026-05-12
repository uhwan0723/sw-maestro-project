package com.soma2026.tikitalka.domain.usecase

import com.soma2026.tikitalka.domain.model.Issue
import com.soma2026.tikitalka.domain.model.PagedResult
import com.soma2026.tikitalka.domain.repository.IssueRepository

class GetIssuesUseCase(
    private val repository: IssueRepository,
) {
    suspend operator fun invoke(
        tag: String? = null,
        page: Int = 0,
        size: Int = 10,
        sort: String = "LATEST",
    ): Result<PagedResult<Issue>> = repository.getIssues(tag, page, size, sort)
}