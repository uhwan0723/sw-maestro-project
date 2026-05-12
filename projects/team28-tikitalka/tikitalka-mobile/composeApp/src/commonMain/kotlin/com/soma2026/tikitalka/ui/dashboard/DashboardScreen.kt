package com.soma2026.tikitalka.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.soma2026.tikitalka.domain.model.Issue
import com.soma2026.tikitalka.presentation.dashboard.DashboardEffect
import com.soma2026.tikitalka.presentation.dashboard.DashboardIntent
import com.soma2026.tikitalka.presentation.dashboard.DashboardState
import com.soma2026.tikitalka.presentation.dashboard.DashboardViewModel
import com.soma2026.tikitalka.ui.theme.TikiTalkaTheme
import com.soma2026.tikitalka.ui.util.toRelativeTimeString
import org.koin.compose.viewmodel.koinViewModel

@Composable
fun DashboardScreen(
    onNavigateToDetail: (String) -> Unit = {},
    viewModel: DashboardViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is DashboardEffect.NavigateToDetail -> onNavigateToDetail(effect.issueId)
                is DashboardEffect.ShowError -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    DashboardContent(
        state = state,
        snackbarHostState = snackbarHostState,
        onIssueClick = { issueId ->
            viewModel.handleIntent(DashboardIntent.SelectIssue(issueId))
        },
        onLoadMore = {
            viewModel.handleIntent(DashboardIntent.LoadMore)
        },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun DashboardContent(
    state: DashboardState,
    snackbarHostState: SnackbarHostState = remember { SnackbarHostState() },
    onIssueClick: (issueId: String) -> Unit,
    onLoadMore: () -> Unit = {},
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "티키 News",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
            )
        },
        snackbarHost = {
            SnackbarHost(snackbarHostState) { data ->
                Snackbar(snackbarData = data)
            }
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            when {
                state.isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                state.errorMessage != null -> {
                    Text(
                        text = "뉴스를 불러오지 못했습니다.",
                        modifier = Modifier.align(Alignment.Center),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
                state.issues.isEmpty() -> {
                    Text(
                        text = "표시할 뉴스가 없습니다.",
                        modifier = Modifier.align(Alignment.Center),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                else -> {
                    val listState = rememberLazyListState()

                    val reachedEnd by remember {
                        derivedStateOf {
                            val lastVisible = listState.layoutInfo.visibleItemsInfo.lastOrNull()
                            val total = listState.layoutInfo.totalItemsCount
                            lastVisible != null && lastVisible.index >= total - 3
                        }
                    }

                    LaunchedEffect(reachedEnd) {
                        if (reachedEnd && !state.isLastPage) onLoadMore()
                    }

                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        item { Spacer(modifier = Modifier.height(8.dp)) }
                        items(state.issues, key = { it.id }) { issue ->
                            IssueCard(
                                issue = issue,
                                onClick = { onIssueClick(issue.id) },
                            )
                        }
                        if (state.isLoadingMore) {
                            item {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(16.dp),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    CircularProgressIndicator()
                                }
                            }
                        }
                        item { Spacer(modifier = Modifier.height(8.dp)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun IssueCard(
    issue: Issue,
    onClick: () -> Unit,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .clickable(onClick = onClick),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 2.dp,
    ) {
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 20.dp)) {
                // 태그 + 시간
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    TagBadge(tag = issue.tag)
                    Text(
                        text = issue.publishedAt.toRelativeTimeString(),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                // 제목
                Text(
                    text = issue.title,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )

                Spacer(modifier = Modifier.height(6.dp))

                // 요약
                Text(
                    text = issue.summary,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )

                Spacer(modifier = Modifier.height(12.dp))

                // 출처 + 요약 보기
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = if (issue.source.length > 30) issue.source.take(30) + "…" else issue.source,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = "읽어 보기 →",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
        }
    }
}

@Composable
private fun TagBadge(tag: String) {
    Box(
        modifier = Modifier
            .clip(MaterialTheme.shapes.extraSmall)
            .background(MaterialTheme.colorScheme.primaryContainer),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = tag.uppercase(),
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onPrimaryContainer,
        )
    }
}

// region Preview

private val previewIssues = listOf(
    Issue(
        id = "1",
        title = "음바페, 레알 마드리드와 결별설... 파리 복귀 가능성 제기",
        summary = "음바페가 레알 마드리드와의 불화설이 계속되는 가운데, 프랑스 현지 매체들이 파리 생제르맹 복귀 가능성을 연이어 보도하고 있다.",
        tag = "TRANSFER",
        publishedAt = "2025-05-10T08:00:00Z",
        hotnessScore = 98,
        url = "",
        source = "L'Equipe",
    ),
    Issue(
        id = "2",
        title = "손흥민, 토트넘 잔류 확정... 새 계약 서명 임박",
        summary = "손흥민이 토트넘 홋스퍼와 새 계약 협상을 마무리하며 잔류가 사실상 확정됐다. 계약 기간은 2년으로 알려졌다.",
        tag = "CONTRACT",
        publishedAt = "2025-05-09T18:00:00Z",
        hotnessScore = 91,
        url = "",
        source = "The Athletic",
    ),
    Issue(
        id = "3",
        title = "챔피언스리그 8강 대진 확정... 레알 vs 맨시티 빅매치 성사",
        summary = "UEFA 챔피언스리그 8강 대진 추첨 결과, 레알 마드리드와 맨체스터 시티가 맞대결을 펼치게 됐다.",
        tag = "UCL",
        publishedAt = "2025-05-09T06:00:00Z",
        hotnessScore = 85,
        url = "",
        source = "UEFA",
    ),
)

@Preview
@Composable
private fun DashboardContentPreview() {
    TikiTalkaTheme {
        DashboardContent(
            state = DashboardState(issues = previewIssues),
            onIssueClick = {},
        )
    }
}

@Preview
@Composable
private fun DashboardContentDarkPreview() {
    TikiTalkaTheme(darkTheme = true) {
        DashboardContent(
            state = DashboardState(issues = previewIssues),
            onIssueClick = {},
        )
    }
}

@Preview
@Composable
private fun DashboardContentLoadingPreview() {
    TikiTalkaTheme {
        DashboardContent(
            state = DashboardState(isLoading = true),
            onIssueClick = {},
        )
    }
}

@Preview
@Composable
private fun DashboardContentEmptyPreview() {
    TikiTalkaTheme {
        DashboardContent(
            state = DashboardState(),
            onIssueClick = {},
        )
    }
}

// endregion
