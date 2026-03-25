import com.android.build.gradle.LibraryExtension

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory = rootProject.layout.buildDirectory.dir("../../build").get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// Older plugins (e.g. media_projection_creator) omit `namespace` required by AGP 8+.
subprojects {
    plugins.withId("com.android.library") {
        extensions.configure<LibraryExtension>("android") {
            if (!namespace.isNullOrBlank()) {
                return@configure
            }
            val manifestFile = project.file("src/main/AndroidManifest.xml")
            if (!manifestFile.exists()) {
                return@configure
            }
            val pkg = Regex("package=\"([^\"]+)\"").find(manifestFile.readText())?.groupValues?.get(1)
            if (pkg != null) {
                namespace = pkg
            }
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
