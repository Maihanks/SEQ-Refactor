package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass9Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass9 subject = new GodClass9();
        assertEquals("v2", subject.m0_bigswitch(2));
    }

}
