package com.soma2026.tikitalka.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.soma2026.tikitalka.navigation.Screen
import com.soma2026.tikitalka.ui.chat.ChatScreen
import com.soma2026.tikitalka.ui.dashboard.DashboardScreen
import com.soma2026.tikitalka.ui.issuedetail.IssueDetailScreen
import com.soma2026.tikitalka.ui.theme.TikiTalkaTheme
import org.jetbrains.compose.resources.painterResource
import tikitalka.composeapp.generated.resources.Res
import tikitalka.composeapp.generated.resources.ico_bot_fs_chatbot
import tikitalka.composeapp.generated.resources.ico_bot_fs_feed
import tikitalka.composeapp.generated.resources.ico_bot_ts_chatbot
import tikitalka.composeapp.generated.resources.ico_bot_ts_feed

@Composable
fun App() {
    TikiTalkaTheme {
        val navController = rememberNavController()
        val navBackStackEntry by navController.currentBackStackEntryAsState()
        val currentRoute = navBackStackEntry?.destination?.route
        val showNavBar = currentRoute != Screen.IssueDetail.route

        Column(modifier = Modifier.fillMaxSize()) {
            val bottomInset = if (showNavBar) 72.dp else 0.dp
            Box(
                modifier =
                    Modifier
                        .weight(1f)
                        .consumeWindowInsets(WindowInsets(bottom = bottomInset)),
            ) {
                NavHost(
                    navController = navController,
                    startDestination = Screen.Dashboard.route,
                ) {
                    composable(Screen.Dashboard.route) {
                        DashboardScreen(
                            onNavigateToDetail = { issueId ->
                                navController.navigate(Screen.IssueDetail.createRoute(issueId))
                            },
                        )
                    }
                    composable(Screen.Chat.route) {
                        ChatScreen()
                    }
                    composable(
                        route = Screen.IssueDetail.route,
                        arguments = listOf(navArgument("id") { type = NavType.StringType }),
                    ) { backStackEntry ->
                        val id = backStackEntry.arguments?.getString("id") ?: return@composable
                        IssueDetailScreen(
                            issueId = id,
                            onNavigateBack = { navController.popBackStack() },
                        )
                    }
                }
            }

            if (showNavBar) {
                NavigationBar(
                    modifier = Modifier.height(72.dp),
                    containerColor = MaterialTheme.colorScheme.surface,
                    tonalElevation = 0.dp,
                ) {
                    val isDashboard = currentRoute == Screen.Dashboard.route
                    val isChat = currentRoute == Screen.Chat.route

                    val itemColors =
                        NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = Color.Transparent,
                            unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                            unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant,
                        )

                    NavigationBarItem(
                        selected = isDashboard,
                        onClick = {
                            navController.navigate(Screen.Dashboard.route) {
                                popUpTo(Screen.Dashboard.route) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = {
                            Icon(
                                modifier = Modifier.size(24.dp),
                                painter = painterResource(if (isDashboard) Res.drawable.ico_bot_ts_feed else Res.drawable.ico_bot_fs_feed),
                                contentDescription = "피드",
                            )
                        },
                        label = { Text("피드", style = MaterialTheme.typography.labelSmall) },
                        colors = itemColors,
                    )
                    NavigationBarItem(
                        selected = isChat,
                        onClick = {
                            navController.navigate(Screen.Chat.route) {
                                popUpTo(Screen.Dashboard.route) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = {
                            Icon(
                                modifier = Modifier.size(24.dp),
                                painter = painterResource(if (isChat) Res.drawable.ico_bot_ts_chatbot else Res.drawable.ico_bot_fs_chatbot),
                                contentDescription = "챗봇",
                            )
                        },
                        label = { Text("챗봇", style = MaterialTheme.typography.labelSmall) },
                        colors = itemColors,
                    )
                }
            }
        }
    }
}
