package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass3Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass3 subject = new GodClass3();
        assertEquals("v2", subject.m0_bigswitch(2));
    }

}
