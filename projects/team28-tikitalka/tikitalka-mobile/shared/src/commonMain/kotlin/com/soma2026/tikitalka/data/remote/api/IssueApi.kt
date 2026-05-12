package com.soma2026.tikitalka.data.remote.api

import com.soma2026.tikitalka.data.remote.dto.IssueDto
import com.soma2026.tikitalka.data.remote.dto.PagedIssueDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.parameter

class IssueApi(private val client: HttpClient) {

    suspend fun getIssues(
        tag: String?,
        page: Int,
        size: Int,
        sort: String,
    ): PagedIssueDto = client.get("api/news") {
        tag?.let { parameter("tag", it) }
        parameter("page", page)
        parameter("size", size)
        parameter("sort", sort)
    }.body()

    suspend fun getIssueDetail(id: String): IssueDto =
        client.get("api/news/$id").body()
}
