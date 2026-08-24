package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass6Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass6 subject = new LeafClass6();
        assertEquals("v2", subject.leafSwitch(2));
    }

}
