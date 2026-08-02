package org.seqrefactor.sidecar;

import com.github.mauricioaniche.ck.CK;
import com.google.gson.GsonBuilder;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

public final class MetricsCommand {

    public MetricsResult analyze(Path srcDir) {
        List<MetricsResult.ClassMetrics> classes = new ArrayList<>();
        new CK().calculate(srcDir.toString(), result -> classes.add(new MetricsResult.ClassMetrics(
                result.getClassName(),
                result.getCbo(),
                result.getLcom(),
                result.getWmc(),
                result.getRfc(),
                result.getLoc())));
        return new MetricsResult(classes);
    }

    public int runFromCli(String[] args) throws IOException {
        CliArgs cliArgs = CliArgs.parse(args);
        Path srcDir = Paths.get(cliArgs.require("src"));
        Path outPath = Paths.get(cliArgs.require("out"));

        MetricsResult result = analyze(srcDir);
        writeJson(result, outPath);
        return 0;
    }

    private void writeJson(MetricsResult result, Path outPath) throws IOException {
        String json = new GsonBuilder().setPrettyPrinting().create().toJson(result);
        Path parent = outPath.toAbsolutePath().getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Files.writeString(outPath, json);
    }
}
