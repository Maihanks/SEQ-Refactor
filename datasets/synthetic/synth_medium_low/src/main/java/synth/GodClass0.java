package synth;

/** Generated God Class container (seqrefactor.synth.generator). Deliberately
 * a God Class: 3 planted method-level smell(s) plus filler
 * methods, so it is a real structural prerequisite of each smell it contains
 * (decomposing it would move the methods below). Do not "clean up". */
public class GodClass0 {

    public int filler0(int x) {
        if (x > 0) {
            return x + 1;
        }
        return x - 1;
    }

    public int filler1(int x) {
        if (x > 0) {
            return x + 1;
        }
        return x - 1;
    }

    public int filler2(int x) {
        if (x > 0) {
            return x + 1;
        }
        return x - 1;
    }

    public int filler3(int x) {
        if (x > 0) {
            return x + 1;
        }
        return x - 1;
    }

    public int filler4(int x) {
        if (x > 0) {
            return x + 1;
        }
        return x - 1;
    }

    // planted: s2 (BigSwitch)
    public String m0_bigswitch(int code) {
        switch (code) {
            case 0:
                return "zero";
            case 1:
                return "one";
            case 2:
                return "two";
            case 3:
                return "three";
            default:
                return "other";
        }
    }

    // planted: s3 (BigSwitch)
    public String m1_bigswitch(int code) {
        switch (code) {
            case 0:
                return "zero";
            case 1:
                return "one";
            case 2:
                return "two";
            case 3:
                return "three";
            default:
                return "other";
        }
    }

    // planted: s4 (LongMethod)
    public int m2_longmethod(int seed) {
        int total = seed;
        total = total + 1;
        total = total + 2;
        total = total + 3;
        total = total + 4;
        total = total + 5;
        total = total + 6;
        total = total + 7;
        total = total + 8;
        total = total + 9;
        total = total + 10;
        total = total * 2;
        total = total - seed;
        return total;
    }

}
