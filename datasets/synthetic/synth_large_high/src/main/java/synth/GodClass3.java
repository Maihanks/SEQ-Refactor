package synth;

/** Generated God Class container (seqrefactor.synth.generator). Deliberately
 * a God Class: 2 planted method-level smell(s) plus filler
 * methods, so it is a real structural prerequisite of each smell it contains
 * (decomposing it would move the methods below). Do not "clean up". */
public class GodClass3 {

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

    public int filler5(int x) {
        if (x > 0) {
            return x + 1;
        }
        return x - 1;
    }

    // planted: s11 (MessageChains)
    public String m0_messagechains(String input) {
        return input.trim().toLowerCase().replace('a', 'b').substring(0, 3);
    }

    // planted: s12 (BigSwitch)
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

}
