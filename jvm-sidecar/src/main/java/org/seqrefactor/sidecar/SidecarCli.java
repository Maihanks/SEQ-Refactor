package org.seqrefactor.sidecar;

import java.util.Arrays;

public final class SidecarCli {

    private SidecarCli() {
    }

    public static void main(String[] args) {
        if (args.length == 0) {
            printUsageAndExit();
            return;
        }

        String subcommand = args[0];
        String[] rest = Arrays.copyOfRange(args, 1, args.length);

        try {
            switch (subcommand) {
                case "test":
                    new TestRunnerCommand().runFromCli(rest);
                    break;
                case "metrics":
                    new MetricsCommand().runFromCli(rest);
                    break;
                default:
                    printUsageAndExit();
            }
        } catch (Exception e) {
            System.err.println("Sidecar internal error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    private static void printUsageAndExit() {
        System.err.println("Usage: sidecar <test|metrics> [options]");
        System.err.println("  test    --src <dir> --test-src <dir> [--classpath <paths>] --out <path.json>");
        System.err.println("  metrics --src <dir> --out <path.json>");
        System.exit(2);
    }
}
