package org.siloserver.silo.tv.testing

import android.app.Application
import android.content.pm.ActivityInfo
import androidx.activity.ComponentActivity
import androidx.test.core.app.ApplicationProvider
import org.junit.rules.ExternalResource
import org.robolectric.Shadows.shadowOf

/** Registers the Compose host only in Robolectric, never in a release APK. */
class ComposeActivityRule : ExternalResource() {
    override fun before() {
        val app = ApplicationProvider.getApplicationContext<Application>()
        val activity = ActivityInfo().apply {
            name = ComponentActivity::class.java.name
            packageName = app.packageName
            applicationInfo = app.applicationInfo
            theme = android.R.style.Theme_Material_Light_NoActionBar
        }
        shadowOf(app.packageManager).addOrUpdateActivity(activity)
    }
}
