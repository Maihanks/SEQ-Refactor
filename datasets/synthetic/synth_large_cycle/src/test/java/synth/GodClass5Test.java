package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass5Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass5 subject = new GodClass5();
        assertEquals("v2", subject.m0_bigswitch(2));
    }

}
