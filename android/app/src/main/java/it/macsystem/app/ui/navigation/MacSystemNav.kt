package it.macsystem.app.ui.navigation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import it.macsystem.app.ui.components.MacSystemTopBar
import it.macsystem.app.ui.screens.AboutScreen
import it.macsystem.app.ui.screens.BrandsScreen
import it.macsystem.app.ui.screens.HomeScreen
import it.macsystem.app.ui.screens.PickupScreen
import it.macsystem.app.ui.screens.StoresScreen
import it.macsystem.app.ui.screens.SupportChatScreen
import it.macsystem.app.ui.screens.WebScreen
import it.macsystem.app.ui.theme.MacNavy
import it.macsystem.app.ui.theme.MacSurface
import it.macsystem.app.web.MacSystemUrls
import java.net.URLDecoder
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

private sealed class TabDestination(
    val route: String,
    val label: String,
    val icon: ImageVector,
) {
    data object Home : TabDestination("tab/home", "Home", Icons.Default.Home)
    data object Catalog : TabDestination("tab/catalog", "Catalogo", Icons.Default.Inventory2)
    data object Brands : TabDestination("tab/brands", "Marchi", Icons.Default.Verified)
    data object Account : TabDestination("tab/account", "Account", Icons.Default.Person)
    data object More : TabDestination("tab/more", "Altro", Icons.Default.MoreHoriz)
}

private val secondaryRoutes = setOf("stores", "support", "pickup", "about")

private fun isWebRoute(route: String?): Boolean {
    return route?.startsWith("web/") == true
}

private fun isTabSelected(tab: TabDestination, currentRoute: String?): Boolean {
    if (currentRoute == null) return false
    return when (tab) {
        TabDestination.Home -> currentRoute == TabDestination.Home.route || currentRoute in secondaryRoutes
        else -> currentRoute == tab.route
    }
}

private fun navigateToHome(navController: NavHostController) {
    val currentRoute = navController.currentBackStackEntry?.destination?.route
    if (currentRoute == TabDestination.Home.route) {
        return
    }

    val poppedToHome = navController.popBackStack(TabDestination.Home.route, inclusive = false)
    if (!poppedToHome) {
        navController.navigate(TabDestination.Home.route) {
            popUpTo(navController.graph.id) {
                inclusive = true
                saveState = true
            }
            launchSingleTop = true
            restoreState = true
        }
    }
}

private fun navigateToTab(navController: NavHostController, route: String) {
    if (route == TabDestination.Home.route) {
        navigateToHome(navController)
        return
    }

    navController.navigate(route) {
        popUpTo(navController.graph.findStartDestination().id) {
            saveState = true
        }
        launchSingleTop = true
        restoreState = true
    }
}

@Composable
fun MacSystemAppRoot() {
    val navController = rememberNavController()
    val tabs = listOf(
        TabDestination.Home,
        TabDestination.Catalog,
        TabDestination.Brands,
        TabDestination.Account,
        TabDestination.More,
    )

    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val showBottomBar = !isWebRoute(currentRoute)

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar(containerColor = MacSurface) {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = isTabSelected(tab, currentRoute),
                            onClick = { navigateToTab(navController, tab.route) },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = MacNavy,
                                selectedTextColor = MacNavy,
                                indicatorColor = MacNavy.copy(alpha = 0.08f),
                            ),
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = TabDestination.Home.route,
            modifier = Modifier.padding(padding),
        ) {
            composable(TabDestination.Home.route) {
                Scaffold(
                    topBar = { MacSystemTopBar(title = "", showLogo = true) },
                ) { inner ->
                    HomeScreen(
                        modifier = Modifier.padding(inner),
                        onNavigate = { route ->
                            when (route) {
                                "catalog" -> navigateToTab(navController, TabDestination.Catalog.route)
                                "brands" -> navigateToTab(navController, TabDestination.Brands.route)
                                "pickup" -> navController.navigate("pickup")
                                "support" -> navController.navigate("support")
                                "stores" -> navController.navigate("stores")
                            }
                        },
                        onSearch = { query ->
                            val encoded = URLEncoder.encode(query, StandardCharsets.UTF_8)
                            navController.navigate("web/search?url=$encoded")
                        },
                    )
                }
            }

            composable(TabDestination.Catalog.route) {
                WebScreen(
                    title = "Catalogo",
                    url = MacSystemUrls.CATALOG,
                    showBack = false,
                    onBack = { navigateToHome(navController) },
                )
            }

            composable(TabDestination.Brands.route) {
                BrandsScreen(
                    onBrandSelected = { brand ->
                        val encoded = URLEncoder.encode(brand.searchKeyword, StandardCharsets.UTF_8)
                        navController.navigate("web/brand?url=$encoded")
                    },
                    onOpenAllBrands = {
                        navController.navigate("web/brands?url=brands")
                    },
                )
            }

            composable(TabDestination.Account.route) {
                WebScreen(
                    title = "Account",
                    url = MacSystemUrls.LOGIN,
                    showBack = false,
                    onBack = { navigateToHome(navController) },
                )
            }

            composable(TabDestination.More.route) {
                Scaffold(
                    topBar = { MacSystemTopBar(title = "Altro", showLogo = false) },
                ) { inner ->
                    Column(
                        modifier = Modifier
                            .padding(inner)
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        MoreMenuItem("Ritiro merci H24") { navController.navigate("pickup") }
                        MoreMenuItem("Assistenza tecnica") { navController.navigate("support") }
                        MoreMenuItem("Punti vendita") { navController.navigate("stores") }
                        MoreMenuItem("Contatti sul sito") {
                            navController.navigate("web/contacts?url=contacts")
                        }
                        MoreMenuItem("Info app") {
                            navController.navigate("about")
                        }
                    }
                }
            }

            composable("about") {
                AboutScreen()
            }

            composable("stores") {
                StoresScreen(
                    onOpenWebContacts = {
                        navController.navigate("web/contacts?url=contacts")
                    },
                )
            }

            composable("support") {
                SupportChatScreen()
            }

            composable("pickup") {
                PickupScreen()
            }

            composable(
                route = "web/{kind}?url={url}",
                arguments = listOf(
                    navArgument("kind") { type = NavType.StringType },
                    navArgument("url") {
                        type = NavType.StringType
                        defaultValue = ""
                    },
                ),
            ) { entry ->
                val kind = entry.arguments?.getString("kind").orEmpty()
                val raw = entry.arguments?.getString("url").orEmpty()
                val decoded = URLDecoder.decode(raw, StandardCharsets.UTF_8.toString())
                val url = when (kind) {
                    "search" -> MacSystemUrls.search(decoded)
                    "brand" -> MacSystemUrls.search(decoded)
                    "brands" -> MacSystemUrls.BRANDS
                    "contacts" -> MacSystemUrls.STORES
                    else -> decoded.ifBlank { MacSystemUrls.HOME }
                }
                val title = when (kind) {
                    "search", "brand" -> "Ricerca prodotti"
                    "brands" -> "Marchi"
                    "contacts" -> "Contatti"
                    else -> "Mac System"
                }
                WebScreen(
                    title = title,
                    url = url,
                    showBack = true,
                    onBack = { navController.popBackStack() },
                )
            }
        }
    }
}

@Composable
private fun MoreMenuItem(
    label: String,
    onClick: () -> Unit,
) {
    androidx.compose.material3.Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(18.dp),
            style = MaterialTheme.typography.titleMedium,
        )
    }
}
