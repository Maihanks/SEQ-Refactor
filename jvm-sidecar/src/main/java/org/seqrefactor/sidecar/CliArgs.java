package org.seqrefactor.sidecar;

import java.util.HashMap;
import java.util.Map;

final class CliArgs {

    private final Map<String, String> values;

    private CliArgs(Map<String, String> values) {
        this.values = values;
    }

    static CliArgs parse(String[] args) {
        Map<String, String> map = new HashMap<>();
        for (int i = 0; i < args.length; i++) {
            String key = args[i];
            if (!key.startsWith("--")) {
                throw new IllegalArgumentException("Unexpected argument: " + key);
            }
            if (i + 1 >= args.length) {
                throw new IllegalArgumentException("Missing value for argument: " + key);
            }
            map.put(key.substring(2), args[++i]);
        }
        return new CliArgs(map);
    }

    String require(String name) {
        String value = values.get(name);
        if (value == null) {
            throw new IllegalArgumentException("Missing required argument: --" + name);
        }
        return value;
    }

    String getOrDefault(String name, String defaultValue) {
        return values.getOrDefault(name, defaultValue);
    }
}
