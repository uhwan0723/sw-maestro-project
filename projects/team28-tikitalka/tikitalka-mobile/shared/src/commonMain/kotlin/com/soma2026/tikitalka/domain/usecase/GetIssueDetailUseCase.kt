package com.soma2026.tikitalka.domain.usecase

import com.soma2026.tikitalka.domain.model.Issue
import com.soma2026.tikitalka.domain.repository.IssueRepository

class GetIssueDetailUseCase(
    private val repository: IssueRepository,
) {
    suspend operator fun invoke(id: String): Result<Issue> = repository.getIssueDetail(id)
}