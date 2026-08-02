package org.seqrefactor.sidecar;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TestRunnerCommandTest {

    @Test
    void reportsOnePassAndOneFailure(@TempDir Path tempDir) throws IOException {
        Path srcDir = tempDir.resolve("src");
        Path testSrcDir = tempDir.resolve("test");
        Files.createDirectories(srcDir);
        Files.createDirectories(testSrcDir);

        Files.writeString(srcDir.resolve("Calculator.java"), """
                public class Calculator {
                    public int add(int a, int b) {
                        return a + b;
                    }
                }
                """);

        Files.writeString(testSrcDir.resolve("CalculatorTest.java"), """
                import org.junit.jupiter.api.Test;
                import static org.junit.jupiter.api.Assertions.assertEquals;

                class CalculatorTest {
                    @Test
                    void additionWorks() {
                        assertEquals(4, new Calculator().add(2, 2));
                    }

                    @Test
                    void additionFailsIntentionally() {
                        assertEquals(5, new Calculator().add(2, 2));
                    }
                }
                """);

        TestRunResult result = new TestRunnerCommand().run(srcDir, testSrcDir, List.of());

        assertTrue(result.getCompileErrors().isEmpty());
        assertEquals(2, result.getTestsRun());
        assertEquals(1, result.getTestsPassed());
        assertEquals(1, result.getTestsFailed());
        assertFalse(result.isSuccess());
        assertEquals(1, result.getFailures().size());
        assertTrue(result.getFailures().get(0).getTest().contains("CalculatorTest"));
    }

    @Test
    void reportsCompileErrorsInsteadOfThrowing(@TempDir Path tempDir) throws IOException {
        Path srcDir = tempDir.resolve("src");
        Path testSrcDir = tempDir.resolve("test");
        Files.createDirectories(srcDir);
        Files.createDirectories(testSrcDir);

        Files.writeString(testSrcDir.resolve("Broken.java"), """
                public class Broken {
                    public void method( {
                    }
                }
                """);

        TestRunResult result = new TestRunnerCommand().run(srcDir, testSrcDir, List.of());

        assertFalse(result.getCompileErrors().isEmpty());
        assertFalse(result.isSuccess());
        assertEquals(0, result.getTestsRun());
        assertEquals(0, result.getTestsPassed());
        assertEquals(0, result.getTestsFailed());
    }
}
