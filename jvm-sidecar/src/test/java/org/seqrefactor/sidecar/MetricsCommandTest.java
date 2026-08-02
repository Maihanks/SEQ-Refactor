package org.seqrefactor.sidecar;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertTrue;

class MetricsCommandTest {

    @Test
    void computesMetricsForACoupledLowCohesionClass(@TempDir Path tempDir) throws IOException {
        Path srcDir = tempDir.resolve("src");
        Files.createDirectories(srcDir);

        Files.writeString(srcDir.resolve("Widget.java"), """
                public class Widget {
                    private int a;
                    private int b;
                    private Helper helper = new Helper();

                    public void methodA() {
                        a = 1;
                    }

                    public void methodB() {
                        b = 2;
                    }

                    public void useHelper() {
                        helper.doWork();
                    }
                }
                """);

        Files.writeString(srcDir.resolve("Helper.java"), """
                public class Helper {
                    void doWork() {
                    }
                }
                """);

        MetricsResult result = new MetricsCommand().analyze(srcDir);

        Optional<MetricsResult.ClassMetrics> widget = result.getClasses().stream()
                .filter(classMetrics -> classMetrics.getClassName().equals("Widget"))
                .findFirst();

        assertTrue(widget.isPresent());
        assertTrue(widget.get().getCbo() >= 1);
        assertTrue(widget.get().getWmc() >= 1);
        assertTrue(widget.get().getRfc() >= 1);
        assertTrue(widget.get().getLoc() > 0);
        assertTrue(widget.get().getLcom() >= 0);
    }
}
