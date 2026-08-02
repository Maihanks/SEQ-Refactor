package org.seqrefactor.sidecar;

import com.google.gson.annotations.SerializedName;

import java.util.List;

public final class MetricsResult {

    private final List<ClassMetrics> classes;

    public MetricsResult(List<ClassMetrics> classes) {
        this.classes = classes;
    }

    public List<ClassMetrics> getClasses() {
        return classes;
    }

    public static final class ClassMetrics {

        @SerializedName("class")
        private final String className;
        private final int cbo;
        private final int lcom;
        private final int wmc;
        private final int rfc;
        private final int loc;

        public ClassMetrics(String className, int cbo, int lcom, int wmc, int rfc, int loc) {
            this.className = className;
            this.cbo = cbo;
            this.lcom = lcom;
            this.wmc = wmc;
            this.rfc = rfc;
            this.loc = loc;
        }

        public String getClassName() {
            return className;
        }

        public int getCbo() {
            return cbo;
        }

        public int getLcom() {
            return lcom;
        }

        public int getWmc() {
            return wmc;
        }

        public int getRfc() {
            return rfc;
        }

        public int getLoc() {
            return loc;
        }
    }
}
