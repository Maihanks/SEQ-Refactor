package synth;

/** Generated God Class container (seqrefactor.synth.generator). Deliberately
 * a God Class: 2 planted method-level smell(s) plus filler
 * methods, so it is a real structural prerequisite of each smell it contains
 * (decomposing it would move the methods below). Do not "clean up". */
public class GodClass1 {

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

    // planted: s5 (MessageChains)
    public String m0_messagechains(String input) {
        return input.trim().toLowerCase().replace('a', 'b').substring(0, 3);
    }

    // planted: s6 (LongMethod)
    public int m1_longmethod(int seed) {
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
