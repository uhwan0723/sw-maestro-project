package com.soma2026.tikitalka.ui.issuedetail

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.soma2026.tikitalka.domain.model.Issue
import com.soma2026.tikitalka.domain.service.TranslationLanguage
import com.soma2026.tikitalka.presentation.issuedetail.IssueDetailEffect
import com.soma2026.tikitalka.presentation.issuedetail.IssueDetailIntent
import com.soma2026.tikitalka.presentation.issuedetail.IssueDetailState
import com.soma2026.tikitalka.presentation.issuedetail.IssueDetailViewModel
import com.soma2026.tikitalka.ui.theme.TikiTalkaTheme
import com.soma2026.tikitalka.ui.util.toRelativeTimeString
import org.jetbrains.compose.resources.painterResource
import org.koin.compose.viewmodel.koinViewModel
import tikitalka.composeapp.generated.resources.Res
import tikitalka.composeapp.generated.resources.ico_btn_back

@Composable
fun IssueDetailScreen(
    issueId: String,
    onNavigateBack: () -> Unit,
    viewModel: IssueDetailViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(issueId) {
        viewModel.load(issueId)
    }

    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is IssueDetailEffect.NavigateBack -> onNavigateBack()
                is IssueDetailEffect.ShowError -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    IssueDetailContent(
        state = state,
        snackbarHostState = snackbarHostState,
        onBack = { viewModel.handleIntent(IssueDetailIntent.NavigateBack) },
        onSelectLanguage = { viewModel.handleIntent(IssueDetailIntent.SelectLanguage(it)) },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun IssueDetailContent(
    state: IssueDetailState,
    snackbarHostState: SnackbarHostState = remember { SnackbarHostState() },
    onBack: () -> Unit = {},
    onSelectLanguage: (TranslationLanguage) -> Unit = {},
) {
    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = "원문",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            painter = painterResource(Res.drawable.ico_btn_back),
                            contentDescription = "뒤로 가기",
                            tint = MaterialTheme.colorScheme.onSurface,
                        )
                    }
                },
                colors =
                    TopAppBarDefaults.topAppBarColors(
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
            modifier =
                Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
        ) {
            when {
                state.isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }

                state.errorMessage != null -> {
                    Text(
                        text = state.errorMessage ?: "",
                        modifier =
                            Modifier
                                .align(Alignment.Center)
                                .padding(horizontal = 32.dp),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error,
                    )
                }

                state.issue != null -> {
                    IssueDetailBody(
                        issue = state.issue!!,
                        selectedLanguage = state.selectedLanguage,
                        translatedContent = state.translatedContent,
                        isTranslating = state.isTranslating,
                        onSelectLanguage = onSelectLanguage,
                    )
                }
            }
        }
    }
}

@Composable
private fun IssueDetailBody(
    issue: Issue,
    selectedLanguage: TranslationLanguage,
    translatedContent: String?,
    isTranslating: Boolean,
    onSelectLanguage: (TranslationLanguage) -> Unit,
) {
    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
    ) {
        // 태그 + 출처 + 시간
        Row(verticalAlignment = Alignment.CenterVertically) {
            TagBadge(tag = issue.tag)
            Spacer(modifier = Modifier.weight(1f))
            Text(
                text = issue.source,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = " · ${issue.publishedAt.toRelativeTimeString()}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // 제목
        Text(
            text = issue.title,
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.onSurface,
        )

        Spacer(modifier = Modifier.height(16.dp))
        HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f))
        Spacer(modifier = Modifier.height(16.dp))

        // 요약
        Text(
            text = "요약",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = issue.summary,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        if (!issue.originalContent.isNullOrBlank()) {
            Spacer(modifier = Modifier.height(20.dp))
            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f))
            Spacer(modifier = Modifier.height(20.dp))

            // 본문 헤더 + 언어 토글
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "본문",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                )
                Spacer(modifier = Modifier.weight(1f))
                LanguageToggle(
                    selected = selectedLanguage,
                    onSelect = onSelectLanguage,
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            if (isTranslating) {
                Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                }
            } else {
                Text(
                    text = translatedContent ?: issue.originalContent ?: "",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
    }
}

@Composable
private fun LanguageToggle(
    selected: TranslationLanguage,
    onSelect: (TranslationLanguage) -> Unit,
) {
    Row(
        modifier =
            Modifier
                .clip(RoundedCornerShape(20.dp))
                .background(MaterialTheme.colorScheme.surfaceVariant),
    ) {
        TranslationLanguage.entries.forEach { language ->
            val isSelected = selected == language
            Box(
                modifier =
                    Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(
                            if (isSelected) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.surfaceVariant
                            },
                        ).clickable { onSelect(language) }
                        .padding(horizontal = 12.dp, vertical = 4.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = language.label,
                    style = MaterialTheme.typography.labelSmall,
                    color =
                        if (isSelected) {
                            MaterialTheme.colorScheme.onPrimary
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        },
                )
            }
        }
    }
}

@Composable
private fun TagBadge(tag: String) {
    Box(
        modifier =
            Modifier
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

private val previewIssue =
    Issue(
        id = "1",
        title = "음바페, 레알 마드리드와 결별설... 파리 복귀 가능성 제기",
        summary = "음바페가 레알 마드리드와의 불화설이 계속되는 가운데, 프랑스 현지 매체들이 파리 생제르맹 복귀 가능성을 연이어 보도하고 있다.",
        tag = "transfer",
        publishedAt = "2026-05-08T05:20:00",
        hotnessScore = 98,
        url = "https://example.com/article",
        source = "L'Equipe",
        originalContent =
            "음바페는 지난 시즌 레알 마드리드에서 기대 이하의 성적을 기록했다. " +
                "팀 내 불화설이 끊이지 않는 가운데 현지 매체들은 그의 파리 복귀 가능성을 잇달아 보도하고 있다. " +
                "특히 PSG 구단주가 재영입 의사를 밝힌 것으로 알려져 이적 시장의 최대 이슈로 떠오르고 있다." +
                "",
    )

@Preview
@Composable
private fun IssueDetailPreview() {
    TikiTalkaTheme {
        IssueDetailContent(state = IssueDetailState(issue = previewIssue))
    }
}

@Preview
@Composable
private fun IssueDetailDarkPreview() {
    TikiTalkaTheme(darkTheme = true) {
        IssueDetailContent(state = IssueDetailState(issue = previewIssue))
    }
}

@Preview
@Composable
private fun IssueDetailLoadingPreview() {
    TikiTalkaTheme {
        IssueDetailContent(state = IssueDetailState(isLoading = true))
    }
}

@Preview
@Composable
private fun IssueDetailErrorPreview() {
    TikiTalkaTheme {
        IssueDetailContent(state = IssueDetailState(errorMessage = "뉴스를 불러오지 못했습니다"))
    }
}

// endregion
