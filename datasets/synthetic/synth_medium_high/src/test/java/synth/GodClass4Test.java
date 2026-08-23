package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass4Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass4 subject = new GodClass4();
        assertEquals("two", subject.m0_bigswitch(2));
    }

}
