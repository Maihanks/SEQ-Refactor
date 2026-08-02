package org.seqrefactor.sidecar;

import com.google.gson.GsonBuilder;

import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.engine.support.descriptor.MethodSource;
import org.junit.platform.launcher.Launcher;
import org.junit.platform.launcher.LauncherDiscoveryRequest;
import org.junit.platform.launcher.TestIdentifier;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;
import org.junit.platform.launcher.listeners.SummaryGeneratingListener;
import org.junit.platform.launcher.listeners.TestExecutionSummary;

import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import java.io.File;
import java.io.IOException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public final class TestRunnerCommand {

    public TestRunResult run(Path srcDir, Path testSrcDir, List<String> extraClasspath) throws IOException {
        List<Path> sources = new ArrayList<>(collectJavaFiles(srcDir));
        sources.addAll(collectJavaFiles(testSrcDir));
        if (sources.isEmpty()) {
            throw new IllegalArgumentException("No .java files found under " + srcDir + " or " + testSrcDir);
        }

        Path outputDir = Files.createTempDirectory("seq-sidecar-test-");
        String classpath = buildClasspath(extraClasspath);

        try {
            List<String> compileErrors = compile(sources, outputDir, classpath);
            if (!compileErrors.isEmpty()) {
                return TestRunResult.compileFailure(compileErrors);
            }
            return executeTests(outputDir, extraClasspath);
        } finally {
            deleteRecursively(outputDir);
        }
    }

    public int runFromCli(String[] args) throws IOException {
        CliArgs cliArgs = CliArgs.parse(args);
        Path srcDir = Paths.get(cliArgs.require("src"));
        Path testSrcDir = Paths.get(cliArgs.require("test-src"));
        Path outPath = Paths.get(cliArgs.require("out"));
        List<String> extraClasspath = splitClasspath(cliArgs.getOrDefault("classpath", ""));

        TestRunResult result = run(srcDir, testSrcDir, extraClasspath);
        writeJson(result, outPath);
        return 0;
    }

    private List<String> compile(List<Path> sources, Path outputDir, String classpath) throws IOException {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("No system Java compiler available; run the sidecar on a JDK, not a JRE.");
        }

        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        try (StandardJavaFileManager fileManager = compiler.getStandardFileManager(diagnostics, null, null)) {
            Iterable<? extends JavaFileObject> units = fileManager.getJavaFileObjectsFromPaths(sources);
            List<String> options = List.of("-d", outputDir.toString(), "-classpath", classpath);
            boolean ok = compiler.getTask(null, fileManager, diagnostics, options, null, units).call();
            if (ok) {
                return List.of();
            }

            List<String> errors = diagnostics.getDiagnostics().stream()
                    .filter(d -> d.getKind() == Diagnostic.Kind.ERROR)
                    .map(this::formatDiagnostic)
                    .collect(Collectors.toList());
            if (errors.isEmpty()) {
                errors = List.of("Compilation failed with no diagnostic details available.");
            }
            return errors;
        }
    }

    private String formatDiagnostic(Diagnostic<? extends JavaFileObject> diagnostic) {
        String source = diagnostic.getSource() == null ? "<unknown>" : diagnostic.getSource().toString();
        return source + ":" + diagnostic.getLineNumber() + ": " + diagnostic.getMessage(null);
    }

    private TestRunResult executeTests(Path outputDir, List<String> extraClasspath) throws IOException {
        List<URL> urls = new ArrayList<>();
        urls.add(outputDir.toUri().toURL());
        for (String entry : extraClasspath) {
            urls.add(Paths.get(entry).toUri().toURL());
        }

        ClassLoader previousLoader = Thread.currentThread().getContextClassLoader();
        // selectClasspathRoots() resolves test classes through the thread's context
        // classloader, so the freshly compiled temp output dir must be added there -
        // it is not on this JVM's own classpath.
        try (URLClassLoader testClassLoader = new URLClassLoader(urls.toArray(new URL[0]), previousLoader)) {
            Thread.currentThread().setContextClassLoader(testClassLoader);

            LauncherDiscoveryRequest request = LauncherDiscoveryRequestBuilder.request()
                    .selectors(DiscoverySelectors.selectClasspathRoots(Set.of(outputDir)))
                    .build();

            Launcher launcher = LauncherFactory.create();
            SummaryGeneratingListener listener = new SummaryGeneratingListener();
            launcher.registerTestExecutionListeners(listener);
            launcher.execute(request);

            return buildResult(listener.getSummary());
        } finally {
            Thread.currentThread().setContextClassLoader(previousLoader);
        }
    }

    private TestRunResult buildResult(TestExecutionSummary summary) {
        List<TestRunResult.Failure> failures = summary.getFailures().stream()
                .map(failure -> new TestRunResult.Failure(describe(failure.getTestIdentifier()), describeFailure(failure)))
                .collect(Collectors.toList());

        return new TestRunResult(
                (int) summary.getTestsFoundCount(),
                (int) summary.getTestsSucceededCount(),
                (int) summary.getTestsFailedCount(),
                failures,
                List.of());
    }

    private String describe(TestIdentifier identifier) {
        return identifier.getSource()
                .filter(MethodSource.class::isInstance)
                .map(MethodSource.class::cast)
                .map(source -> source.getClassName() + "#" + source.getMethodName())
                .orElse(identifier.getDisplayName());
    }

    private String describeFailure(TestExecutionSummary.Failure failure) {
        Throwable exception = failure.getException();
        return exception == null ? "" : String.valueOf(exception.getMessage());
    }

    private List<Path> collectJavaFiles(Path root) throws IOException {
        if (!Files.isDirectory(root)) {
            return List.of();
        }
        try (Stream<Path> walk = Files.walk(root)) {
            return walk.filter(Files::isRegularFile)
                    .filter(path -> path.toString().endsWith(".java"))
                    .collect(Collectors.toList());
        }
    }

    private String buildClasspath(List<String> extraClasspath) {
        List<String> entries = new ArrayList<>();
        entries.add(System.getProperty("java.class.path"));
        entries.addAll(extraClasspath);
        return String.join(File.pathSeparator, entries);
    }

    private List<String> splitClasspath(String raw) {
        if (raw.isBlank()) {
            return List.of();
        }
        return Arrays.stream(raw.split(Pattern.quote(File.pathSeparator)))
                .filter(entry -> !entry.isBlank())
                .collect(Collectors.toList());
    }

    private void deleteRecursively(Path root) throws IOException {
        if (!Files.exists(root)) {
            return;
        }
        try (Stream<Path> walk = Files.walk(root)) {
            walk.sorted(Comparator.reverseOrder()).forEach(path -> {
                try {
                    Files.delete(path);
                } catch (IOException ignored) {
                    // best-effort cleanup of the temp compile output
                }
            });
        }
    }

    private void writeJson(TestRunResult result, Path outPath) throws IOException {
        String json = new GsonBuilder().setPrettyPrinting().create().toJson(result);
        Path parent = outPath.toAbsolutePath().getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Files.writeString(outPath, json);
    }
}
