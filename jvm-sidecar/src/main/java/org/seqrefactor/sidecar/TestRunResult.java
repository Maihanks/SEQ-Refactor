package org.seqrefactor.sidecar;

import com.google.gson.annotations.SerializedName;

import java.util.List;

public final class TestRunResult {

    private final boolean success;

    @SerializedName("tests_run")
    private final int testsRun;

    @SerializedName("tests_passed")
    private final int testsPassed;

    @SerializedName("tests_failed")
    private final int testsFailed;

    private final List<Failure> failures;

    @SerializedName("compile_errors")
    private final List<String> compileErrors;

    public TestRunResult(int testsRun, int testsPassed, int testsFailed,
                          List<Failure> failures, List<String> compileErrors) {
        this.testsRun = testsRun;
        this.testsPassed = testsPassed;
        this.testsFailed = testsFailed;
        this.failures = failures;
        this.compileErrors = compileErrors;
        this.success = compileErrors.isEmpty() && testsFailed == 0;
    }

    static TestRunResult compileFailure(List<String> compileErrors) {
        return new TestRunResult(0, 0, 0, List.of(), compileErrors);
    }

    public boolean isSuccess() {
        return success;
    }

    public int getTestsRun() {
        return testsRun;
    }

    public int getTestsPassed() {
        return testsPassed;
    }

    public int getTestsFailed() {
        return testsFailed;
    }

    public List<Failure> getFailures() {
        return failures;
    }

    public List<String> getCompileErrors() {
        return compileErrors;
    }

    public static final class Failure {

        private final String test;
        private final String message;

        public Failure(String test, String message) {
            this.test = test;
            this.message = message;
        }

        public String getTest() {
            return test;
        }

        public String getMessage() {
            return message;
        }
    }
}
