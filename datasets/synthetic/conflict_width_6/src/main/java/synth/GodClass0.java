package synth;

/** Generated God Class container (seqrefactor.synth.generator, severity
 * 0.333). Deliberately a God Class: 6
 * planted method-level smell(s) plus filler methods and a fixed padding
 * block (decouples detection from severity, see module docstring), so it
 * is a real structural prerequisite of each smell it contains. Do not
 * "clean up". */
public class GodClass0 {
    // padding 0
    // padding 1
    // padding 2
    // padding 3
    // padding 4
    // padding 5
    // padding 6
    // padding 7
    // padding 8
    // padding 9
    // padding 10
    // padding 11
    // padding 12
    // padding 13
    // padding 14
    // padding 15
    // padding 16
    // padding 17
    // padding 18
    // padding 19
    // padding 20
    // padding 21
    // padding 22
    // padding 23
    // padding 24
    // padding 25
    // padding 26
    // padding 27
    // padding 28
    // padding 29
    // padding 30
    // padding 31
    // padding 32
    // padding 33
    // padding 34
    // padding 35
    // padding 36
    // padding 37
    // padding 38
    // padding 39
    // padding 40
    // padding 41
    // padding 42
    // padding 43
    // padding 44
    // padding 45
    // padding 46
    // padding 47
    // padding 48
    // padding 49
    // padding 50
    // padding 51
    // padding 52
    // padding 53
    // padding 54
    // padding 55
    // padding 56
    // padding 57
    // padding 58
    // padding 59
    // padding 60
    // padding 61
    // padding 62
    // padding 63
    // padding 64
    // padding 65
    // padding 66
    // padding 67
    // padding 68
    // padding 69
    // padding 70
    // padding 71
    // padding 72
    // padding 73
    // padding 74
    // padding 75
    // padding 76
    // padding 77
    // padding 78
    // padding 79
    // padding 80
    // padding 81
    // padding 82
    // padding 83
    // padding 84
    // padding 85
    // padding 86
    // padding 87
    // padding 88
    // padding 89
    // padding 90
    // padding 91
    // padding 92
    // padding 93
    // padding 94
    // padding 95
    // padding 96
    // padding 97
    // padding 98
    // padding 99

    // planted: s2 (BigSwitch, severity 0.8)
    public String m0_bigswitch(int code) {
        switch (code) {
            case 0: return "v0";
            case 1: return "v1";
            case 2: return "v2";
            case 3: return "v3";
            case 4: return "v4";
            case 5: return "v5";
            default: return "other";
        }
    }

    // planted: s3 (BigSwitch, severity 0.7)
    public String m1_bigswitch(int code) {
        switch (code) {
            case 0: return "v0";
            case 1: return "v1";
            case 2: return "v2";
            case 3: return "v3";
            case 4: return "v4";
            default: return "other";
        }
    }

    // planted: s4 (LongMethod, severity 1.0)
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
        total = total + 11;
        if (seed >= 0) { total = total + 100; }
        if (seed >= 0) { total = total + 101; }
        if (seed >= 0) { total = total + 102; }
        if (seed >= 0) { total = total + 103; }
        if (seed >= 0) { total = total + 104; }
        if (seed >= 0) { total = total + 105; }
        if (seed >= 0) { total = total + 106; }
        if (seed >= 0) { total = total + 107; }
        if (seed >= 0) { total = total + 108; }
        return total;
    }

    // planted: s5 (MessageChains, severity 0.6)
    public String m3_messagechains(String input) {
        String result = input.trim().toLowerCase().replace('a', 'b').substring(0, 3);
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        return result;
    }

    // planted: s6 (LongMethod, severity 0.8)
    public int m4_longmethod(int seed) {
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
        total = total + 11;
        if (seed >= 0) { total = total + 100; }
        if (seed >= 0) { total = total + 101; }
        if (seed >= 0) { total = total + 102; }
        if (seed >= 0) { total = total + 103; }
        if (seed >= 0) { total = total + 104; }
        if (seed >= 0) { total = total + 105; }
        if (seed >= 0) { total = total + 106; }
        return total;
    }

    // planted: s7 (MessageChains, severity 0.7)
    public String m5_messagechains(String input) {
        String result = input.trim().toLowerCase().replace('a', 'b').substring(0, 3);
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        if (input.length() >= 0) { result = result + "x"; }
        return result;
    }

}
